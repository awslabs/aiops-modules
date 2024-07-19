from aws_cdk import (
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_assets as s3_assets,
    aws_codecommit as codecommit,
    aws_s3_deployment as s3deploy,
    aws_sagemaker as sagemaker,
    CfnOutput,
    CustomResource,
    Duration,
    RemovalPolicy,
    Stack,
    DefaultStackSynthesizer,
)
from aws_cdk.aws_sagemaker import CfnFeatureGroup
from aws_cdk.aws_iam import (
    CompositePrincipal,
    ManagedPolicy,
    PolicyDocument,
    PolicyStatement,
    Role,
    ServicePrincipal,
)
from aws_cdk.aws_lambda import Architecture
from constructs import Construct
import os
from cdk_nag import NagSuppressions


class LabelingInitStack(Stack):
    def __init__(self, scope: Construct, id: str, props: dict, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        if props.repo_type == "CODECOMMIT":
            self.seed_code_commit_repo(props.repo_name, props.branch_name)

        self.data_bucket = self.create_assets_bucket()
        seed_assets_role = self.create_seed_assets_role()
        bucket_deployment: s3deploy.BucketDeployment = (
            self.seed_initial_assets_to_bucket(self.data_bucket)
        )
        self.feature_group = seed_labels_to_feature_store(
            self, seed_assets_role, self.data_bucket, bucket_deployment, props
        )
        self.model_package_group = create_model_package_group(self, props)

        CfnOutput(
            self,
            "modelPackageGroup",
            value=self.model_package_group.model_package_group_name,
            description="The name of the modelpackage group where models are stored in sagemaker model registry",
            export_name="aiopsModelPackageGroup",
        )

        CfnOutput(
            self,
            "aiopsfeatureGroup",
            value=self.feature_group.feature_group_name,
            description="The name of the feature group where features are stored in feature store",
            export_name="aiopsfeatureGroup",
        )

        CfnOutput(
            self,
            "aiopsDataBucket",
            value=self.data_bucket.bucket_name,
            description="The Name of the data bucket",
            export_name="aiopsDataBucket",
        )

    def seed_code_commit_repo(self, repo_name: str, branch_name: str):
        # Only uploading minimal code from this repo for the stack to work, excluding seed assets and doc
        directory_asset = s3_assets.Asset(
            self,
            "SeedCodeAsset",
            path=os.path.join(os.path.dirname(__file__), "../../.."),
            exclude=[
                "*.js",
                "node_modules",
                "doc",
                "*.d.ts",
                "cdk.out",
                "model.tar.gz",
                ".git",
                ".python-version",
            ],
        )
        codecommit.Repository(
            self,
            "Repository",
            repository_name=repo_name,
            code=codecommit.Code.from_asset(directory_asset, branch_name),
        )

    def create_assets_bucket(self) -> s3.Bucket:
        # Create default bucket where all assets are stored
        data_bucket = s3.Bucket(
            self,
            "LabelingDataBucket",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            cors=[
                s3.CorsRule(
                    allowed_headers=[],
                    allowed_methods=[s3.HttpMethods.GET],
                    allowed_origins=["*"],
                )
            ],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        NagSuppressions.add_resource_suppressions(
            data_bucket,
            [
                {
                    "id": "AwsSolutions-S1",
                    "reason": "Artifact Bucket does not need access logs enabled for sample",
                }
            ],
        )

        # Bucket policy to deny access to HTTP requests
        my_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.DENY,
            actions=["s3:*"],
            resources=[data_bucket.bucket_arn, data_bucket.arn_for_objects("*")],
            principals=[iam.AnyPrincipal()],
            conditions={"Bool": {"aws:SecureTransport": "false"}},
        )

        # Allow Cfn exec and deploy permissions
        cfn_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:*"],
            resources=[data_bucket.bucket_arn, data_bucket.arn_for_objects("*")],
            principals=[ServicePrincipal("cloudformation.amazonaws.com")],
        )

        # Allow cdk roles to read/write permissions
        cdk_bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:*"],
            resources=[data_bucket.bucket_arn, data_bucket.arn_for_objects("*")],
            principals=[
                iam.ArnPrincipal(
                    f"arn:aws:iam::{Stack.of(self).account}:role/cdk-hnb659fds-deploy-role-{Stack.of(self).account}-{Stack.of(self).region}"
                )
            ],
        )

        data_bucket.add_to_resource_policy(my_bucket_policy)
        data_bucket.add_to_resource_policy(cfn_bucket_policy)
        data_bucket.add_to_resource_policy(cdk_bucket_policy)

        return data_bucket

    def seed_initial_assets_to_bucket(
        self, data_bucket: s3.Bucket
    ) -> s3deploy.BucketDeployment:
        # Deploy assets required by the pipeline, like the dataset and templates for labeling jobs
        return s3deploy.BucketDeployment(
            self,
            "AssetInit",
            memory_limit=1024,
            sources=[s3deploy.Source.asset(os.path.join("./lib/assets"))],
            destination_bucket=data_bucket,
            destination_key_prefix="pipeline/assets",
        )

    def create_seed_assets_role(self) -> iam.Role:
        policy = PolicyDocument(
            statements=[
                PolicyStatement(
                    resources=[
                        f"arn:aws:s3:::{self.data_bucket.bucket_name}/*",
                        f"arn:aws:s3:::{self.data_bucket.bucket_name}",
                    ],
                    actions=["s3:*"],
                ),
                PolicyStatement(
                    actions=["sagemaker:PutRecord"],
                    resources=[
                        f"arn:aws:sagemaker:{self.region}:{self.account}:feature-group/{self._feature_group_name}"
                    ],
                ),
                PolicyStatement(
                    actions=["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
                    resources=[
                        f"arn:aws:ecr:{self.region}:{self.account}:repository/{DefaultStackSynthesizer.DEFAULT_IMAGE_ASSETS_REPOSITORY_NAME}"
                    ],
                ),
                PolicyStatement(actions=["ecr:GetAuthorizationToken"], resources=["*"]),
            ]
        )

        return Role(
            self,
            "FeatureGroupRole",
            assumed_by=CompositePrincipal(
                ServicePrincipal("sagemaker.amazonaws.com"),
                ServicePrincipal("lambda.amazonaws.com"),
            ),
            inline_policies={"lambdaPolicy": policy},
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFeatureStoreAccess"
                ),
                ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

    _feature_group_name = "tag-quality-inspection"


def seed_labels_to_feature_store(
    self,
    role: iam.Role,
    data_bucket: s3.Bucket,
    bucket_deployment: s3deploy.BucketDeployment,
    props: dict,
) -> sagemaker.CfnFeatureGroup:
    offline_store_config = {
        "S3StorageConfig": {"S3Uri": f"s3://{data_bucket.bucket_name}/feature-store/"}
    }

    feature_group = sagemaker.CfnFeatureGroup(
        self,
        "MyCfnFeatureGroup",
        event_time_feature_name="event_time",
        feature_definitions=[
            CfnFeatureGroup.FeatureDefinitionProperty(
                feature_name="source_ref", feature_type="String"
            ),
            CfnFeatureGroup.FeatureDefinitionProperty(
                feature_name="image_width", feature_type="Integral"
            ),
            CfnFeatureGroup.FeatureDefinitionProperty(
                feature_name="image_height", feature_type="Integral"
            ),
            CfnFeatureGroup.FeatureDefinitionProperty(
                feature_name="image_depth", feature_type="Integral"
            ),
            CfnFeatureGroup.FeatureDefinitionProperty(
                feature_name="annotations", feature_type="String"
            ),
            CfnFeatureGroup.FeatureDefinitionProperty(
                feature_name="event_time", feature_type="Fractional"
            ),
            CfnFeatureGroup.FeatureDefinitionProperty(
                feature_name="labeling_job", feature_type="String"
            ),
            CfnFeatureGroup.FeatureDefinitionProperty(
                feature_name="status", feature_type="String"
            ),
        ],
        feature_group_name=self._feature_group_name,
        record_identifier_feature_name="source_ref",
        description="Stores bounding box dataset for quality inspection",
        offline_store_config=offline_store_config,
        role_arn=role.role_arn,
    )

    seed_labels_function = lambda_.DockerImageFunction(
        self,
        "SeedLabelsToFeatureStoreFunction",
        code=lambda_.DockerImageCode.from_image_asset(
            os.path.join(
                os.path.dirname(__file__), "../lambda/seed_labels_to_feature_store"
            )
        ),
        architecture=Architecture.X86_64,
        function_name="SeedLabelsToFeatureStoreFunction",
        memory_size=1024,
        role=role,
        timeout=Duration.seconds(300),
        log_retention=logs.RetentionDays.ONE_WEEK,
    )

    custom_resource = CustomResource(
        self,
        "SeedLabelsCustomResource",
        service_token=seed_labels_function.function_arn,
        properties={
            # "feature_group_name": props.feature_group_name,
            "labels_uri": f"s3://{data_bucket.bucket_name}/pipeline/assets/labels/labels.csv"
        },
    )

    feature_group.node.add_dependency(bucket_deployment)

    custom_resource.node.add_dependency(feature_group)

    return feature_group


def create_model_package_group(self, props: dict) -> sagemaker.CfnModelPackageGroup:
    cfn_model_package_group = sagemaker.CfnModelPackageGroup(
        self,
        "MyCfnModelPackageGroup",
        model_package_group_name=props.model_package_group_name,
        model_package_group_description=props.model_package_group_description,
    )

    cfn_model_package_group.apply_removal_policy(RemovalPolicy.DESTROY)

    return cfn_model_package_group
