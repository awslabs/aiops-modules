from typing import Any, Optional
import aws_cdk as cdk
import yaml
from aws_cdk import (
    Stack,
)
from settings import ApplicationSettings
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression
from cdk_nag import AwsSolutionsChecks
from lib.stacks.init import LabelingInitStack as InitStack
from lib.stacks.labeling_pipeline import LabelingPipelineStack
from lib.stacks.statemachine_pipeline import ExecuteStateMachinePipeline

app = cdk.App()


class AppConfig(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Load settings from settings.py
        app_settings = ApplicationSettings()

        self.repo_type: str = app_settings.parameters.repoType
        self.repo_name: str = app_settings.parameters.repoName
        self.branch_name: str = app_settings.parameters.branchName
        self.github_repo_owner: str = app_settings.parameters.githubRepoOwner
        self.github_connection_arn: Optional[str] = app_settings.parameters.githubConnectionArn
        self.pipeline_assets_prefix: str = app_settings.parameters.pipeline_assets_prefix
        self.labeling_job_private_workteam_arn: Optional[
            str] = app_settings.parameters.labeling_job_private_workteam_arn
        self.use_private_workteam_for_labeling: bool = app_settings.parameters.use_private_workteam_for_labeling
        self.use_private_workteam_for_verification: bool = app_settings.parameters.use_private_workteam_for_verification
        self.verification_job_private_workteam_arn: Optional[
            str] = app_settings.parameters.verification_job_private_workteam_arn
        self.max_labels_per_labeling_job: int = app_settings.parameters.max_labels_per_labeling_job
        self.labeling_pipeline_schedule: str = app_settings.parameters.labeling_pipeline_schedule
        self.feature_group_name: str = app_settings.parameters.feature_group_name
        self.model_package_group_name: str = app_settings.parameters.model_package_group_name
        self.model_package_group_description: str = app_settings.parameters.model_package_group_description

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_type": self.repo_type,
            "repo_name": self.repo_name,
            "branch_name": self.branch_name,
            "pipeline_assets_prefix": self.pipeline_assets_prefix,
            "labeling_job_private_workteam_arn": self.labeling_job_private_workteam_arn,
            "use_private_workteam_for_labeling": self.use_private_workteam_for_labeling,
            "use_private_workteam_for_verification": self.use_private_workteam_for_verification,
            "verification_job_private_workteam_arn": self.verification_job_private_workteam_arn,
            "max_labels_per_labeling_job": self.max_labels_per_labeling_job,
            "labeling_pipeline_schedule": self.labeling_pipeline_schedule,
            "feature_group_name": self.feature_group_name,
            "model_package_group_name": self.model_package_group_name,
            "model_package_group_description": self.model_package_group_description,
            "github_repo_owner": self.github_repo_owner,
            "githubConnectionArn": self.github_connection_arn,
        }


def add_security_checks(app: cdk.App, stacks: list[Stack]) -> None:
    suppressions = [
        NagPackSuppression(
            id="AwsSolutions-IAM4",
            reason="Suppress disallowed use of managed policies for increased simplicity as this is a sample. Scope down in production!",
        ),
        NagPackSuppression(
            id="AwsSolutions-IAM5",
            reason="Suppress disallowed use of wildcards in IAM policies for increased simplicity as this is a sample. Scope down in production!",
        ),
        NagPackSuppression(
            id="AwsSolutions-L1",
            reason="Using fixed python version for lambda functions as sample needs to be stable",
        ),
        NagPackSuppression(
            id="AwsSolutions-CB3",
            reason="Suppress warning for use of privileged mode for codebuild, as this is required for docker image build",
        ),
        NagPackSuppression(
            id="AwsSolutions-CB4",
            reason="Suppress required use of KMS for CodeBuild as it incurs additional cost. Consider using KMS for Codebuild in production",
        ),
    ]

    for stack in stacks:
        NagSuppressions.add_stack_suppressions(stack, suppressions)

    AwsSolutionsChecks(verbose=True)


def main() -> None:
    app_config = AppConfig(app, "aiops-config")
    app_config_dict = app_config.to_dict()
    init_stack = InitStack(
        app,
        "aiops-init-stack",
        app_config_dict.get("repo_name", ""),
        app_config_dict.get("branch_name", ""),
        app_config_dict.get("repo_type", ""),
        app_config_dict.get("model_package_group_name", ""),
        app_config_dict.get("model_package_group_description", ""),
        app_config_dict,
    )

    labeling_pipeline_stack = LabelingPipelineStack(
        app, "aiops-labeling-infra-stack", app_config_dict
    )
    # Add the dependency
    labeling_pipeline_stack.add_dependency(init_stack)

    # Statemachine stack
    statemachine_pipeline_stack = ExecuteStateMachinePipeline(
        app, "aiops-statemachine-pipeline", app_config_dict
    )
    statemachine_pipeline_stack.add_dependency(init_stack)
    statemachine_pipeline_stack.add_dependency(labeling_pipeline_stack)

    add_security_checks(
        app, [init_stack, labeling_pipeline_stack, statemachine_pipeline_stack]
    )
    app.synth()


if __name__ == "__main__":
    main()
