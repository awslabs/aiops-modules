# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any

import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as events_targets
import aws_cdk.aws_iam as aws_iam
import aws_cdk.aws_s3 as aws_s3
import aws_cdk.aws_stepfunctions as sfn
from aws_cdk import Aws, Duration, RemovalPolicy, Stack
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct

_logger: logging.Logger = logging.getLogger(__name__)


class MLOPSSFNResources(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        project_name: str,
        deployment_name: str,
        module_name: str,
        model_name: str,
        schedule: str,
        **kwargs: Any,
    ) -> None:
        # MLOPS Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name

        super().__init__(
            scope,
            id,
            description="This stack deploys Example DAGs resources for MLOps",
            **kwargs,
        )
        account: str = Aws.ACCOUNT_ID
        region: str = Aws.REGION

        mlops_assets_bucket = aws_s3.Bucket(
            self,
            id="mlops-sfn-assets-bucket",
            versioned=False,
            # bucket_name=f"{dep_mod}-{account}-{region}",
            removal_policy=RemovalPolicy.DESTROY,
            encryption=aws_s3.BucketEncryption.KMS_MANAGED,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        self.mlops_assets_bucket = mlops_assets_bucket

        # Create Dag IAM Role and policy
        s3_access_statements = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    actions=["s3:List*", "s3:Get*"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[
                        mlops_assets_bucket.bucket_arn,
                        f"{mlops_assets_bucket.bucket_arn}/*",
                    ],
                )
            ]
        )

        # create a role for lambda function
        lambda_role = aws_iam.Role(
            self,
            "LambdaRole",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
            # role_name=r_name,
            path="/",
        )

        # Create the Step Functions Execution Role
        sfn_rule_statements = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    actions=[
                        "events:PutTargets",
                        "events:PutRule",
                        "events:DescribeRule",
                    ],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[f"arn:aws:events:{region}:{account}:rule/StepFunctions*"],
                )
            ]
        )

        sfn_exec_role = aws_iam.Role(
            self,
            "StepFunctionsExecutionRole",
            assumed_by=aws_iam.ServicePrincipal("states.amazonaws.com"),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaRole"),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess"),
            ],
            inline_policies={
                "SfnSMRulePolicy": sfn_rule_statements,
            },
        )
        # sfn_exec_role.add_managed_policy(sfn_rule_policy)

        self.sfn_exec_role = sfn_exec_role

        # Define the IAM role
        sagemaker_execution_role = aws_iam.Role(
            self,
            "SageMakerExecutionRole",
            assumed_by=aws_iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")],
            path="/",
            # role_name=f"SageMakerExecutionRole-{self.stack_name}",
        )

        # Add policy to allow access to S3 bucket and IAM pass role
        mlops_assets_bucket.grant_read_write(sagemaker_execution_role)
        mlops_assets_bucket.grant_read(sfn_exec_role)
        sagemaker_execution_role.grant_pass_role(sfn_exec_role)

        self.sagemaker_execution_role = sagemaker_execution_role
        # self.state_machine_arn = sagemaker_execution_role

        # Create the Step Functions State Machine
        state_machine = sfn.StateMachine(
            self,
            "StateMachine",
            definition_body=sfn.DefinitionBody.from_file("./state_machine.json"),
            state_machine_type=sfn.StateMachineType.STANDARD,
            role=sfn_exec_role,
        )
        self.state_machine_arn = state_machine.state_machine_arn

        sfn_execution_for_lambda = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    actions=["states:StartExecution"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[state_machine.state_machine_arn],
                )
            ]
        )

        # create a lambda function with python runtime and install dependencies from requirementes with docker
        lambda_function = PythonFunction(
            self,
            "LambdaFunction",
            entry="lambda",
            runtime=Runtime.PYTHON_3_12,
            index="handler.py",
            handler="lambda_handler",
            role=lambda_role,
            environment={"STATE_MACHINE_ARN": state_machine.state_machine_arn},
            timeout=Duration.seconds(60),
        )
        self.lambda_function_arn = lambda_function.function_arn

        lambda_role.attach_inline_policy(aws_iam.Policy(self, "SFNExecutionPolicy", document=sfn_execution_for_lambda))
        lambda_role.attach_inline_policy(aws_iam.Policy(self, "S3AccessRole", document=s3_access_statements))

        # Create the EventBridge rule

        event_rule = events.Rule(
            self,
            "MyEventRule",
            schedule=events.Schedule.expression(f"cron({schedule})"),
        )
        # Define the custom input as an event

        custom_input = {
            "config": {
                "bucket": mlops_assets_bucket.bucket_name,
                "prefix": f"{model_name}/scripts/input.yaml",
            }
            # Add more key-value pairs as needed
        }
        event_rule.add_target(
            events_targets.LambdaFunction(
                lambda_function,
                event=events.RuleTargetInput.from_object(custom_input),
            )
        )

        NagSuppressions.add_resource_suppressions(
            self,
            apply_to_children=True,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason="Logs are disabled for demo purposes",
                ),
                NagPackSuppression(
                    id="AwsSolutions-S5",
                    reason="No OAI needed - no one is accessing this data without explicit permissions",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Resource access restricted to MLOPS resources.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Managed Policies are for service account roles only",
                ),
                NagPackSuppression(
                    id="AwsSolutions-SF1",
                    reason="Logs are disabled for demo purposes",
                ),
                NagPackSuppression(
                    id="AwsSolutions-SF2",
                    reason="X-Ray is disabled for demo purposes",
                ),
            ],
        )
