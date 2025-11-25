from typing import Any, List

from aws_cdk import Duration
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
        )

        wait_task = sfn.Wait(self, "WaitForBaselining", time=sfn.WaitTime.duration(Duration.minutes(2)))

        check_task = tasks.LambdaInvoke(
            self,
            "CheckBaselining",
            lambda_function=baselining_lambda,
            payload=sfn.TaskInput.from_object({"action": "check", "job_name.$": "$.Payload.job_name"}),
        )

        # State machine
        definition = (
            start_task.next(wait_task)
            .next(check_task)
            .next(
                sfn.Choice(self, "IsJobComplete")
                .when(
                    sfn.Condition.string_equals("$.Payload.status", "COMPLETED"),
                    sfn.Succeed(self, "JobCompleted"),
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
