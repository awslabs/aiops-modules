"""Seedfarmer module to deploy a Pipeline to promote SageMaker Model Packages."""
import os
from typing import Any, Optional

import aws_cdk as cdk
import aws_cdk.aws_codebuild as codebuild
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as events_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_assets as s3_assets
from constructs import Construct


class SagemakerModelPackagePipelineStack(cdk.Stack):
    """Create a Pipeline to promote Sagemaker Model Packages."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        source_model_package_group_arn: str,
        target_bucket_name: str,
        event_bus_name: Optional[str] = None,
        target_model_package_group_name: Optional[str] = None,
        sagemaker_project_id: Optional[str] = None,
        sagemaker_project_name: Optional[str] = None,
        kms_key_arn: Optional[str] = None,
        retain_on_delete: bool = True,
        **kwargs: Any,
    ) -> None:
        """Create a Pipeline to promote Sagemaker Model Packages.

        Parameters
        ----------
        scope
            Parent of this cdk.Stack, usually an ``App`` or a ``Stage``, but could be any construct
        construct_id
            The construct ID of this cdk.Stack
        source_model_package_group_arn
            The SageMaker Model Package Group ARN to get the latest approved model package
        target_bucket_name
            The S3 bucket name to store model artifacts
        event_bus_name
            The event bus name to listen for sagemaker model package group state changes and trigger
            the pipeline on Approved and Rejected states.
        target_model_package_group_name
            The target model package group name to register the model package being promoted, optional. Defaults None.
            If None, the target model package group name will be the same as the source model package group name.
        sagemaker_project_id
            The SageMaker project id to associate with the model package group.
        sagemaker_project_name
            The SageMaker project name to associate with the model package group.
        kms_key_arn
            The KMS Key ARN to encrypt model artifacts.
        retain_on_delete
            Wether or not to retain model package resources on delete. Defaults True. This applies only
            to the sagemaker model package resources and not to the resources in this stack.
        """
        super().__init__(scope, construct_id, **kwargs)

        self.source_model_package_group_arn = source_model_package_group_arn
        self.target_bucket_name = target_bucket_name

        self.event_bus_name = event_bus_name
        self.target_model_package_group_name = target_model_package_group_name
        self.sagemaker_project_id = sagemaker_project_id
        self.sagemaker_project_name = sagemaker_project_name
        self.kms_key_arn = kms_key_arn
        self.retain_on_delete = retain_on_delete
        self.pipeline_name = f"{construct_id}-Pipeline"

        components = self.split_arn(
            arn=self.source_model_package_group_arn,
            arn_format=cdk.ArnFormat.SLASH_RESOURCE_NAME,
        )

        self.source_account = components.account
        self.source_model_package_group_name = components.resource_name

        self.setup_resources()

        self.setup_outputs()

        self.setup_tags()

    def setup_resources(self) -> None:
        """Deploy resources."""

        self.target_bucket = s3.Bucket.from_bucket_name(
            self, "TargetBucket", self.target_bucket_name
        )

        self.kms_key = (
            kms.Key.from_key_arn(self, "KMSKey", self.kms_key_arn)
            if self.kms_key_arn
            else None
        )

        self.code_asset = self.setup_code_assets()
        self.pipeline = self.setup_pipeline()
        self.rule = self.setup_events()

    def setup_tags(self) -> None:
        """Add cdk.Tags to all resources."""
        cdk.Tags.of(self).add(
            "sagemaker:deployment-stage", cdk.Stack.of(self).stack_name
        )

        if self.sagemaker_project_id:
            cdk.Tags.of(self).add("sagemaker:project-id", self.sagemaker_project_id)

        if self.sagemaker_project_name:
            cdk.Tags.of(self).add("sagemaker:project-name", self.sagemaker_project_name)

    def setup_outputs(self) -> None:
        """Setups outputs and metadata."""
        metadata = {
            "PipelineArn": self.pipeline.pipeline_arn,
            "PipelineName": self.pipeline.pipeline_name,
        }

        if self.rule:
            metadata["EventRuleArn"] = self.rule.rule_arn
            metadata["EventRuleName"] = self.rule.rule_name

        for key, value in metadata.items():
            cdk.CfnOutput(scope=self, id=key, value=value)

        cdk.CfnOutput(scope=self, id="metadata", value=self.to_json_string(metadata))

    def setup_pipeline(self) -> codepipeline.Pipeline:
        """Create a CodePipeline to promote models."""
        metadata_path = "./model/model_config.json"
        artifacts_path = "./model/model_artifacts"

        pipeline = codepipeline.Pipeline(
            self,
            "CodePipeline",
            pipeline_name=self.pipeline_name,
            enable_key_rotation=True,
        )

        # Source Stage
        source_stage = pipeline.add_stage(stage_name="Source")
        source_artifact = codepipeline.Artifact()
        source_action = codepipeline_actions.S3SourceAction(
            action_name="SourceAction",
            bucket=self.code_asset.bucket,
            bucket_key=self.code_asset.s3_object_key,
            output=source_artifact,
            trigger=codepipeline_actions.S3Trigger.POLL,
        )
        source_stage.add_action(source_action)

        # Build Stage
        build_stage = pipeline.add_stage(stage_name="Build")
        build_artifact = codepipeline.Artifact()
        build_project = self.setup_pipeline_build_project(
            metadata_path=metadata_path, artifacts_path=artifacts_path
        )
        build_action = codepipeline_actions.CodeBuildAction(
            action_name="BuildAction",
            input=source_artifact,
            project=build_project,
            outputs=[build_artifact],
        )

        build_stage.add_action(build_action)

        # Deploy Stage
        deploy_stage = pipeline.add_stage(stage_name="Deploy")
        deploy_project = self.setup_pipeline_deploy_project(metadata_path=metadata_path)
        deploy_action = codepipeline_actions.CodeBuildAction(
            action_name="DeployAction",
            input=build_artifact,
            project=deploy_project,
        )

        deploy_stage.add_action(deploy_action)

        return pipeline

    def setup_pipeline_build_project(
        self, metadata_path: str, artifacts_path: str
    ) -> codebuild.PipelineProject:
        """Setup a build project

        Parameters
        ----------
        metadata_path
            The path to store the metadata JSON file.
        artifacts_path
            The path to store model downloaded artifacts.

        Returns
        -------
            A PipelineProject instance.
        """
        env_vars = {
            "MODEL_PACKAGE_GROUP_ARN": codebuild.BuildEnvironmentVariable(
                value=self.source_model_package_group_arn
            ),
            "MODEL_METADATA_PATH": codebuild.BuildEnvironmentVariable(
                value=metadata_path
            ),
            "MODEL_ARTIFACTS_PATH": codebuild.BuildEnvironmentVariable(
                value=artifacts_path
            ),
        }

        cmd = "python3 script/get_model.py -p $MODEL_ARTIFACTS_PATH -o $MODEL_METADATA_PATH -g $MODEL_PACKAGE_GROUP_ARN"
        build_spec = {
            "version": "0.2",
            "phases": {
                "install": {
                    "commands": [
                        "pip install -U pip",
                        "pip install -r script/requirements.txt",
                    ],
                },
                "build": {
                    "commands": [cmd],
                },
            },
            "artifacts": {
                "base-directory": ".",
                "files": ["**/*"],
            },
        }

        role = self.get_pipeline_build_project_role()

        build_project = codebuild.PipelineProject(
            self,
            "BuildProject",
            build_spec=codebuild.BuildSpec.from_object(build_spec),
            environment_variables=env_vars,
            description="Get latest approved model metadata and artifacts from a a SageMaker Model Package Group",
            timeout=cdk.Duration.minutes(30),
            role=role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0
            ),
        )

        return build_project

    def setup_pipeline_deploy_project(
        self, metadata_path: str
    ) -> codebuild.PipelineProject:
        """Setup a deploy project

        Parameters
        ----------
        metadata_path
            The metadata JSON filepath.

        Returns
        -------
            A PipelineProject instance.
        """
        env_vars = {
            "app_prefix": codebuild.BuildEnvironmentVariable(
                value=f"{self.pipeline_name}-DeployProject"
            ),
            "model_metadata_path": codebuild.BuildEnvironmentVariable(
                value=metadata_path
            ),
            "bucket_name": codebuild.BuildEnvironmentVariable(
                value=self.target_bucket.bucket_name
            ),
            "retain_on_delete": codebuild.BuildEnvironmentVariable(
                value=self.retain_on_delete
            ),
            "CDK_DEFAULT_ACCOUNT": codebuild.BuildEnvironmentVariable(
                value=self.account
            ),
            "CDK_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(value=self.region),
        }

        if self.target_model_package_group_name:
            env_vars["model_package_group_name"] = codebuild.BuildEnvironmentVariable(
                value=self.target_model_package_group_name
            )

        if self.kms_key:
            env_vars["kms_key_arn"] = codebuild.BuildEnvironmentVariable(
                value=self.kms_key.key_arn
            )

        build_spec = {
            "version": "0.2",
            "phases": {
                "build": {
                    "commands": [
                        "pip install -U pip",
                        "npm install -g aws-cdk@2.126.0",
                        "pip install -r requirements.txt",
                        'cdk deploy --require-approval never --progress events --app "python app.py"',
                    ]
                }
            },
        }

        role = self.get_pipeline_deploy_project_role()
        project = codebuild.PipelineProject(
            self,
            "DeployProject",
            build_spec=codebuild.BuildSpec.from_object(build_spec),
            environment_variables=env_vars,
            description="Deploy model metadata and model artifacts to another SageMaker Model Package Group.",
            timeout=cdk.Duration.minutes(30),
            role=role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0
            ),
        )

        return project

    def setup_code_assets(self) -> s3_assets.Asset:
        """Deploy seed code to an S3 bucket.

        Returns
        -------
            A Asset instance.
        """
        zip_image = cdk.DockerImage.from_build("images/zip-image")
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "seed_code")

        bundling = cdk.BundlingOptions(
            image=zip_image,
            command=[
                "sh",
                "-c",
                """zip -r /asset-output/code_asset.zip .""",
            ],
            output_type=cdk.BundlingOutput.ARCHIVED,
        )

        code_asset = s3_assets.Asset(
            self,
            "CodeAsset",
            path=path,
            bundling=bundling,
        )

        return code_asset

    def setup_events(self) -> Optional[events.Rule]:
        """Setup an event rule

        The event rule will send SageMaker Model Package State Change events to another EventBus.

        Returns
        -------
            An event rule or None if not event bus name is defined.
        """
        if not self.event_bus_name:
            return None

        eventbus = events.EventBus.from_event_bus_name(
            scope=self, id="EventBus", event_bus_name=self.event_bus_name
        )

        event_pattern = events.EventPattern(
            source=["aws.sagemaker"],
            account=[self.source_account] if self.source_account else None,
            detail_type=["SageMaker Model Package State Change"],
            detail={
                "ModelPackageGroupName": [self.source_model_package_group_name],
                "ModelApprovalStatus": ["Approved", "Rejected"],
            },
        )

        rule = events.Rule(
            self,
            "SageMakerModelPackageStateChangeRule",
            event_bus=eventbus,
            event_pattern=event_pattern,
            description="Rule to trigger a CICD pipeline when SageMaker Model Package state changes",
        )

        target_role = iam.Role(
            self,
            "SageMakerModelPackageStateChangeRuleTargetRole",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
            path="/service-role/",
        )

        target_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "codepipeline:StartPipelineExecution",
                ],
                effect=iam.Effect.ALLOW,
                resources=[self.pipeline.pipeline_arn],
            )
        )

        target = events_targets.CodePipeline(
            pipeline=self.pipeline,
            event_role=target_role,
            retry_attempts=3,
        )

        rule.add_target(target)

        return rule

    def get_pipeline_build_project_role(self) -> iam.Role:
        """Get an IAM Role for the build project"""
        build_project_role = iam.Role(
            scope=self,
            id="BuildProjectRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            path="/service-role/",
        )

        build_project_role_policy = iam.Policy(
            self,
            "BuildProjectRolePolicy",
            document=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        sid="GrantKMSKeyReadOnlyPermissions",
                        actions=[
                            "kms:GenerateDataKey*",
                            "kms:Decrypt",
                            "kms:DescribeKey",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=[
                            f"arn:{self.partition}:kms:{self.region}:{self.source_account}:key/*",
                            f"arn:{self.partition}:kms:{self.region}:{self.account}:key/*",
                        ],
                    ),
                    iam.PolicyStatement(
                        sid="GrantS3ReadOnlyPermissions",
                        actions=["s3:ListBucket", "s3:GetObject*"],
                        effect=iam.Effect.ALLOW,
                        resources=["arn:aws:s3:::*"],
                        conditions={
                            "StringEquals": {"s3:ResourceAccount": self.source_account}
                        },
                    ),
                    iam.PolicyStatement(
                        sid="GrantSageMakerModelPkgReadOnlyPermissions",
                        actions=[
                            "sagemaker:DescribeModelPackageGroup",
                            "sagemaker:DescribeModelPackage",
                            "sagemaker:ListModelPackages",
                        ],
                        effect=iam.Effect.ALLOW,
                        resources=[
                            f"arn:aws:sagemaker:{self.region}:{self.source_account}:model-package/*",
                            self.source_model_package_group_arn,
                        ],
                    ),
                ]
            ),
        )

        build_project_role_policy.attach_to_role(build_project_role)

        if self.kms_key:
            self.kms_key.grant_encrypt_decrypt(build_project_role)

        return build_project_role

    def get_pipeline_deploy_project_role(self) -> iam.Role:
        """Get an IAM Role for the deploy project"""
        role = iam.Role(
            scope=self,
            id="DeployProjectRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            path="/service-role/",
        )

        role.add_to_policy(
            iam.PolicyStatement(
                sid="GrantAssumeRoleOnCDKRoles",
                actions=["sts:AssumeRole"],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:{self.partition}:iam::{self.account}:role/cdk-*-{self.account}-{self.region}"
                ],
            )
        )

        return role
