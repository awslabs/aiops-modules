from typing import Any, List, Optional

from aws_cdk import BundlingOptions, Duration
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
        baseline_instance_count: int = 1,
        baseline_instance_type: str = "ml.m5.xlarge",
        baseline_volume_size_gb: int = 20,
        baseline_max_runtime_seconds: int = 3600,
        schedule_expression: str = "cron(0 2 * * ? *)",
        model_quality_problem_type: Optional[str] = None,
        model_quality_inference_attribute: Optional[str] = None,
        model_quality_probability_attribute: Optional[str] = None,
        model_quality_ground_truth_attribute: Optional[str] = None,
        model_bias_label_header: Optional[str] = None,
        model_bias_headers: Optional[str] = None,
        model_bias_dataset_type: Optional[str] = None,
        model_bias_label_values: Optional[str] = None,
        model_bias_facet_name: Optional[str] = None,
        model_bias_facet_values: Optional[str] = None,
        model_bias_probability_threshold: Optional[str] = None,
        model_bias_model_name: Optional[str] = None,
        model_explainability_label_header: Optional[str] = None,
        model_explainability_headers: Optional[str] = None,
        model_explainability_dataset_type: Optional[str] = None,
        model_explainability_model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda function
        baselining_lambda = lambda_.Function(
            self,
            "BaseliningLambda",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="baselining_handler.lambda_handler",
            code=lambda_.Code.from_asset(
                "sagemaker_model_monitoring/lambda",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_13.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
            timeout=Duration.minutes(15),
            memory_size=2048,
            environment={
                "SAGEMAKER_ROLE_ARN": sagemaker_role_arn,
                "TRAINING_DATA_URI": baseline_training_data_s3_uri,
                "BASELINE_OUTPUT_URI": baseline_output_data_s3_uri,
                "BASELINE_INSTANCE_COUNT": str(baseline_instance_count),
                "BASELINE_INSTANCE_TYPE": baseline_instance_type,
                "BASELINE_VOLUME_SIZE_GB": str(baseline_volume_size_gb),
                "BASELINE_MAX_RUNTIME_SECONDS": str(baseline_max_runtime_seconds),
                "MODEL_QUALITY_PROBLEM_TYPE": model_quality_problem_type,
                "MODEL_QUALITY_INFERENCE_ATTRIBUTE": model_quality_inference_attribute,
                "MODEL_QUALITY_PROBABILITY_ATTRIBUTE": model_quality_probability_attribute,
                "MODEL_QUALITY_GROUND_TRUTH_ATTRIBUTE": model_quality_ground_truth_attribute,
                "MODEL_BIAS_LABEL_HEADER": model_bias_label_header,
                "MODEL_BIAS_HEADERS": model_bias_headers,
                "MODEL_BIAS_DATASET_TYPE": model_bias_dataset_type,
                "MODEL_BIAS_LABEL_VALUES": model_bias_label_values,
                "MODEL_BIAS_FACET_NAME": model_bias_facet_name,
                "MODEL_BIAS_FACET_VALUES": model_bias_facet_values,
                "MODEL_BIAS_PROBABILITY_THRESHOLD": model_bias_probability_threshold,
                "MODEL_BIAS_MODEL_NAME": model_bias_model_name,
                "MODEL_EXPLAINABILITY_LABEL_HEADER": model_explainability_label_header,
                "MODEL_EXPLAINABILITY_HEADERS": model_explainability_headers,
                "MODEL_EXPLAINABILITY_DATASET_TYPE": model_explainability_dataset_type,
                "MODEL_EXPLAINABILITY_MODEL_NAME": model_explainability_model_name,
            },
        )

        # Add IAM permissions for Lambda
        baselining_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:CreateProcessingJob",
                    "sagemaker:DescribeProcessingJob",
                    "iam:PassRole",
                ],
                resources=["*"],
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
                {"action": "start", "monitor_type.$": "$.monitor_type", "endpoint_name": endpoint_name}
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

        # Add CDK-nag suppressions
        NagSuppressions.add_resource_suppressions(
            baselining_lambda.role,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Lambda function uses AWS managed policy for basic execution role",
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Lambda function requires wildcard permissions to invoke SageMaker baselining jobs with dynamic job names",
                }
            ],
            apply_to_children=True,
        )

        NagSuppressions.add_resource_suppressions(
            state_machine.role,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Step Function requires wildcard permissions to invoke Lambda function and access CloudWatch logs",
                }
            ],
            apply_to_children=True,
        )

        # Cron trigger
        rule = events.Rule(self, "BaseliningScheduleRule", schedule=events.Schedule.expression(schedule_expression))

        for monitor_type in enabled_monitors:
            rule.add_target(
                targets.SfnStateMachine(
                    state_machine, input=events.RuleTargetInput.from_object({"monitor_type": monitor_type})
                )
            )
