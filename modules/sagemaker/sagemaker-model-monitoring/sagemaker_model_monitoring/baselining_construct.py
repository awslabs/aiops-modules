import json
from typing import Any, List

from aws_cdk import CustomResource, Duration
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from cdk_nag import NagSuppressions
from constructs import Construct


class BaseliningConstruct(Construct):
    """
    CDK construct for Model Monitoring baseline suggestion.

    Contains a Step Function that runs SageMaker Model Monitoring baselining jobs.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        endpoint_name: str,
        model_bucket_name: str,
        enabled_monitors: List[str],
        sagemaker_role_arn: str,
        baseline_training_data_s3_uri: str,
        baseline_output_data_s3_uri: str,
        schedule_expression: str = "cron(0 2 * * ? *)",
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda function using Docker container image
        # This approach bypasses the 250MB layer limit by using container images (up to 10GB)
        baselining_lambda = lambda_.DockerImageFunction(
            self,
            "BaseliningLambda",
            code=lambda_.DockerImageCode.from_image_asset(
                "sagemaker_model_monitoring/lambda",
                cmd=["baselining_handler.lambda_handler"],
                build_args={
                    "PYTHON_VERSION": "3.13",
                },
            ),
            timeout=Duration.minutes(15),
            memory_size=2048,
            environment={
                "SAGEMAKER_ROLE_ARN": sagemaker_role_arn,
                "LOG_LEVEL": "INFO",
            },
        )

        # Add IAM permissions for Lambda
        baselining_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:CreateProcessingJob",
                    "sagemaker:DescribeProcessingJob",
                ],
                resources=["*"],
            )
        )

        # Add PassRole permission for SageMaker service role
        baselining_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[sagemaker_role_arn],
                conditions={"StringEquals": {"iam:PassedToService": "sagemaker.amazonaws.com"}},
            )
        )

        # Add S3 permissions for baseline data
        baselining_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                ],
                resources=[
                    f"arn:aws:s3:::{baseline_training_data_s3_uri.replace('s3://', '')}*",
                    f"arn:aws:s3:::{baseline_output_data_s3_uri.replace('s3://', '')}*",
                ],
            )
        )

        # CloudWatch Log Group for Step Function
        log_group = logs.LogGroup(
            self,
            "BaseliningStateMachineLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
        )

        # Step Function tasks
        start_task = tasks.LambdaInvoke(
            self,
            "StartBaselining",
            lambda_function=baselining_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "action": "start",
                    "monitor_type.$": "$.monitor_type",
                    "endpoint_name": endpoint_name,
                    "training_data_uri": baseline_training_data_s3_uri,
                    "baseline_output_uri": baseline_output_data_s3_uri,
                }
            ),
            output_path="$.Payload",
        )

        wait_task = sfn.Wait(self, "WaitForBaselining", time=sfn.WaitTime.duration(Duration.minutes(2)))

        check_task = tasks.LambdaInvoke(
            self,
            "CheckBaselining",
            lambda_function=baselining_lambda,
            payload=sfn.TaskInput.from_object({"action": "check", "job_name.$": "$.job_name"}),
            output_path="$.Payload",
        )

        # State machine
        definition = (
            start_task.next(wait_task)
            .next(check_task)
            .next(
                sfn.Choice(self, "IsJobComplete")
                .when(
                    sfn.Condition.string_equals("$.status", "COMPLETED"),
                    sfn.Succeed(self, "JobCompleted"),
                )
                .when(
                    sfn.Condition.string_equals("$.status", "FAILED"),
                    sfn.Fail(
                        self,
                        "JobFailed",
                        cause="Baselining job failed",
                        error="ProcessingJobFailed",
                    ),
                )
                .otherwise(wait_task)
            )
        )

        state_machine = sfn.StateMachine(
            self,
            "BaseliningStateMachine",
            definition=definition,
            timeout=Duration.hours(4),
            tracing_enabled=True,
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ALL,
            ),
        )

        # Cron trigger
        rule = events.Rule(self, "BaseliningScheduleRule", schedule=events.Schedule.expression(schedule_expression))

        for monitor_type in enabled_monitors:
            rule.add_target(
                targets.SfnStateMachine(
                    state_machine, input=events.RuleTargetInput.from_object({"monitor_type": monitor_type})
                )
            )

        # Trigger baseline immediately on deployment (fire-and-forget)
        trigger_lambda = lambda_.Function(
            self,
            "TriggerBaselineLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_inline("""
import boto3
import json
import urllib3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sfn = boto3.client('stepfunctions')
http = urllib3.PoolManager()

def send_response(event, context, status, reason=None):
    response_body = {
        'Status': status,
        'Reason': reason or f'See CloudWatch Log Stream: {context.log_stream_name}',
        'PhysicalResourceId': 'baseline-trigger',
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
    }

    json_response = json.dumps(response_body)
    headers = {'content-type': '', 'content-length': str(len(json_response))}

    try:
        http.request('PUT', event['ResponseURL'], body=json_response, headers=headers)
    except Exception as e:
        logger.error(f"Failed to send response: {e}")

def handler(event, context):
    try:
        logger.info(f"Event: {json.dumps(event)}")
        request_type = event['RequestType']

        if request_type in ['Create', 'Update']:
            state_machine_arn = event['ResourceProperties']['StateMachineArn']
            monitor_types = json.loads(event['ResourceProperties']['MonitorTypes'])

            for monitor_type in monitor_types:
                sfn.start_execution(
                    stateMachineArn=state_machine_arn,
                    input=json.dumps({'monitor_type': monitor_type})
                )

            send_response(event, context, 'SUCCESS', 'Baseline generation triggered')
        elif request_type == 'Delete':
            send_response(event, context, 'SUCCESS', 'Nothing to delete')
        else:
            send_response(event, context, 'SUCCESS', f'No action for {request_type}')

    except Exception as e:
        logger.error(f"Error: {e}")
        send_response(event, context, 'FAILED', str(e))
"""),
            timeout=Duration.seconds(30),
        )

        trigger_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["states:StartExecution"],
                resources=[state_machine.state_machine_arn],
            )
        )

        CustomResource(
            self,
            "TriggerBaselineResource",
            service_token=trigger_lambda.function_arn,
            properties={
                "StateMachineArn": state_machine.state_machine_arn,
                "MonitorTypes": json.dumps(enabled_monitors),
            },
        )

        # Add CDK-nag suppressions
        if trigger_lambda.role:
            NagSuppressions.add_resource_suppressions(
                trigger_lambda.role,
                [
                    {
                        "id": "AwsSolutions-IAM4",
                        "reason": "Lambda function uses AWS managed policy for basic execution role",
                    },
                ],
                apply_to_children=True,
            )

        # Add CDK-nag suppressions
        if baselining_lambda.role:
            NagSuppressions.add_resource_suppressions(
                baselining_lambda.role,
                [
                    {
                        "id": "AwsSolutions-IAM4",
                        "reason": "Lambda function uses AWS managed policy for basic execution role",
                    },
                    {
                        "id": "AwsSolutions-IAM5",
                        "reason": "Lambda function requires wildcard to invoke baselining jobs with dynamic job names",
                    },
                ],
                apply_to_children=True,
            )

        NagSuppressions.add_resource_suppressions(
            state_machine.role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Step Function requires wildcard to invoke Lambda function and access CloudWatch logs",
                }
            ],
            apply_to_children=True,
        )
