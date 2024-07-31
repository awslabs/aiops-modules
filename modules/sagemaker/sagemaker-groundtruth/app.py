from typing import Any
import aws_cdk as cdk
import yaml
from aws_cdk import (
    Stack,
)
from constructs import Construct
from cdk_nag import NagSuppressions
from cdk_nag import AwsSolutionsChecks
from lib.stacks.init import LabelingInitStack as InitStack
from lib.stacks.labeling_pipeline import LabelingPipelineStack
from lib.stacks.statemachine_pipeline import ExecuteStateMachinePipeline

app = cdk.App()


class AppConfig(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        with open("config.yaml") as file:
            config_yaml = yaml.safe_load(file)
        with open("repo_config.yaml") as repo_file:
            repo_config_yaml = yaml.safe_load(repo_file)

        self.repo_type: str = repo_config_yaml["repoType"]
        self.repo_name: str = repo_config_yaml["repoName"]
        self.branch_name: str = repo_config_yaml["branchName"]
        self.github_repo_owner: str = repo_config_yaml["githubRepoOwner"]
        self.github_connection_arn: str = repo_config_yaml["githubConnectionArn"]
        self.pipeline_assets_prefix: str = config_yaml["pipelineAssetsPrefix"]
        self.labeling_job_private_workteam_arn: str = config_yaml[
            "labelingJobPrivateWorkteamArn"
        ]
        self.use_private_workteam_for_labeling: bool = config_yaml[
            "usePrivateWorkteamForLabeling"
        ]
        self.use_private_workteam_for_verification: bool = config_yaml[
            "usePrivateWorkteamForVerification"
        ]
        self.verification_job_private_workteam_arn: str = config_yaml[
            "verificationJobPrivateWorkteamArn"
        ]
        self.max_labels_per_labeling_job: int = config_yaml["maxLabelsPerLabelingJob"]
        self.labeling_pipeline_schedule: str = config_yaml["labelingPipelineSchedule"]
        self.feature_group_name: str = config_yaml["featureGroupName"]
        self.model_package_group_name: str = config_yaml["modelPackageGroupName"]
        self.model_package_group_description: str = config_yaml[
            "modelPackageGroupDescription"
        ]

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
    for stack in stacks:
        NagSuppressions.add_stack_suppressions(
            stack,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Suppress disallowed use of managed policies for increased simplicity as this is a sample. Scope down in production!",
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Suppress disallowed use of wildcards in IAM policies for increased simplicity as this is a sample. Scope down in production!",
                },
                {
                    "id": "AwsSolutions-L1",
                    "reason": "Using fixed python version for lambda functions as sample needs to be stable",
                },
                {
                    "id": "AwsSolutions-CB3",
                    "reason": "Suppress warning for use of privileged mode for codebuild, as this is required for docker image build",
                },
                {
                    "id": "AwsSolutions-CB4",
                    "reason": "Suppress required use of KMS for CodeBuild as it incurs additional cost. Consider using KMS for Codebuild in production",
                },
            ],
        )
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
