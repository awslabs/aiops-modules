from typing import Any
from aws_cdk import (
    aws_iam as iam,
    aws_lambda as lambda_,
    Duration,
    Stack,
    Fn,
)
from aws_cdk.aws_lambda import Architecture
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct
import os
import random
import string


class PipelineAssets(Construct):
    def __init__(
        self, scope: Construct, id: str, props: dict[str, Any], **kwargs: Any
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.props: dict[str, Any] = props
        print(self.props)
        # import the bucket created in init stack
        data_bucket_name = Fn.import_value("aiopsDataBucket")

        feature_group_name: str = props.get("feature_group_name", "")
        labeling_job_private_workteam_arn: str = props.get(
            "labeling_job_private_workteam_arn", ""
        )
        verification_job_private_workteam_arn: str = props.get(
            "verification_job_private_workteam_arn", ""
        )

        # Create execution role for the Step Function pipeline
        pipeline_role = self.create_execution_role(data_bucket_name, props)

        # Create lambda function to check for missing labels
        self.check_missing_labels_lambda = self.create_missing_labels_lambda(
            data_bucket_name, feature_group_name, props, pipeline_role
        )

        # Create lambda function for SageMaker Ground Truth verification job
        self.verification_job_lambda = self.create_run_verification_job_lambda(
            data_bucket_name,
            verification_job_private_workteam_arn,
            props,
            pipeline_role,
        )

        # Create lambda function for SageMaker Ground Truth labeling job
        self.labeling_job_lambda = self.create_run_labeling_job_lambda(
            data_bucket_name, labeling_job_private_workteam_arn, props, pipeline_role
        )

        # Create lambda function to update labels in the feature store
        self.update_feature_store_lambda_function = self.update_feature_store_lambda(
            data_bucket_name, feature_group_name, props, pipeline_role
        )

    def create_execution_role(
        self, data_bucket_name: str, props: dict[str, Any]
    ) -> iam.Role:
        random_string = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        role_name = f"{self.node.id}ExecutionRole{random_string}"
        pipeline_role = iam.Role(
            self,
            role_name,
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
                iam.ServicePrincipal("lambda.amazonaws.com"),
            ),
        )

        pipeline_role.add_to_policy(
            iam.PolicyStatement(
                resources=["*"],
                actions=[
                    "sagemaker:DescribeLabelingJob",
                    "cloudwatch:DescribeLogStreams",
                    "cloudwatch:CreateLogGroup",
                    "cloudwatch:CreateLogStream",
                    "logs:PutLogEvents",
                    "states:StartExecution",
                ],
            )
        )

        pipeline_role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    f"arn:aws:s3:::{data_bucket_name}",
                    f"arn:aws:s3:::{data_bucket_name}/*",
                ],
                actions=["s3:*"],
            )
        )

        pipeline_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess")
        )

        pipeline_role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    f"arn:aws:athena:{Stack.of(self).region}:{Stack.of(self).account}:workgroup/primary"
                ],
                actions=[
                    "athena:StartQueryExecution",
                    "athena:GetQueryExecution",
                    "athena:GetQueryResults",
                    "athena:StopQueryExecution",
                    "athena:GetWorkGroup",
                ],
            )
        )

        pipeline_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")
        )
        pipeline_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        return pipeline_role

    def update_feature_store_lambda(
        self,
        data_bucket_name: str,
        feature_group_name: str,
        props: dict[str, Any],
        role: iam.Role,
    ) -> lambda_.DockerImageFunction:
        return lambda_.DockerImageFunction(
            self,
            "UpdateFeatureStoreLambda",
            code=lambda_.DockerImageCode.from_image_asset(
                os.path.join(
                    os.path.dirname(__file__), "../lambda/update_feature_store"
                )
            ),
            architecture=Architecture.X86_64,
            function_name="UpdateLabelsInFeatureStoreFunction",
            memory_size=1024,
            timeout=Duration.seconds(600),
            role=role,
            environment={
                "ROLE": role.role_arn,
                "FEATURE_GROUP_NAME": feature_group_name,
                "FEATURE_NAME_S3URI": "source_ref",
                "FEATURE_STORE_S3URI": f"s3://{data_bucket_name}/feature-store/",
                "QUERY_RESULTS_S3URI": f"s3://{data_bucket_name}/tmp/feature_store_query_results",
            },
        )

    def create_missing_labels_lambda(
        self,
        data_bucket_name: str,
        feature_group_name: str,
        props: dict[str, Any],
        role: iam.Role,
    ) -> lambda_.DockerImageFunction:
        print(props)
        missing_labels_lambda = lambda_.DockerImageFunction(
            self,
            "CheckMissingLabelsFunction",
            code=lambda_.DockerImageCode.from_image_asset(
                os.path.join(
                    os.path.dirname(__file__), "../lambda/check_missing_labels"
                )
            ),
            architecture=Architecture.X86_64,
            function_name="CheckMissingLabelsFunction",
            memory_size=1024,
            role=role,
            timeout=Duration.seconds(300),
            environment={
                "FEATURE_GROUP_NAME": feature_group_name,
                "FEATURE_NAME_S3URI": "source_ref",
                "INPUT_IMAGES_S3URI": f"s3://{data_bucket_name}/pipeline/assets/images/",
                "QUERY_RESULTS_S3URI": f"s3://{data_bucket_name}/tmp/feature_store_query_results",
            },
        )

        return missing_labels_lambda

    def create_run_labeling_job_lambda(
        self,
        data_bucket_name: str,
        labeling_job_private_workteam_arn: str,
        props: dict[str, Any],
        role: iam.Role,
    ) -> PythonFunction:
        return PythonFunction(
            self,
            "RunLabelingJobLambda",
            entry="lib/lambda/run_labeling_job",
            runtime=lambda_.Runtime.PYTHON_3_11,
            architecture=Architecture.X86_64,
            timeout=Duration.seconds(300),
            role=role,
            environment={
                "BUCKET": data_bucket_name,
                "PREFIX": "pipeline/assets",
                "ROLE": role.role_arn,
                "USE_PRIVATE_WORKTEAM": str(
                    props.get("use_private_workteam_for_labeling")
                ),
                "PRIVATE_WORKTEAM_ARN": labeling_job_private_workteam_arn,
                "MAX_LABELS": str(props.get("max_labels_per_labeling_job")),
            },
        )

    def create_run_verification_job_lambda(
        self,
        data_bucket_name: str,
        verification_job_private_workteam_arn: str,
        props: dict[str, Any],
        role: iam.Role,
    ) -> PythonFunction:
        print(type(data_bucket_name))
        print(props.get("use_private_workteam_for_verification"))
        print(props.get("verification_job_private_workteam_arn"))
        return PythonFunction(
            self,
            "RunVerificationJobLambda",
            entry="lib/lambda/run_verification_job",
            architecture=Architecture.X86_64,
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(300),
            role=role,
            environment={
                "BUCKET": data_bucket_name,
                "PREFIX": "pipeline/assets",
                "ROLE": role.role_arn,
                "USE_PRIVATE_WORKTEAM": str(
                    props.get("use_private_workteam_for_verification")
                ),
                "PRIVATE_WORKTEAM_ARN": verification_job_private_workteam_arn,
            },
        )
