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
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        with open("config.yaml") as file:
            config_yaml = yaml.safe_load(file)
        with open("repo_config.yaml") as repo_file:
            repo_config_yaml = yaml.safe_load(repo_file)

        self.repo_type = repo_config_yaml["repoType"]
        self.repo_name = repo_config_yaml["repoName"]
        self.branch_name = repo_config_yaml["branchName"]
        # self.github_connection_arn = repo_config_yaml['githubConnectionArn']
        # self.github_repo_owner = repo_config_yaml['githubRepoOwner']
        self.pipeline_assets_prefix = config_yaml["pipelineAssetsPrefix"]
        self.labeling_job_private_workteam_arn = config_yaml[
            "labelingJobPrivateWorkteamArn"
        ]
        self.use_private_workteam_for_labeling = config_yaml[
            "usePrivateWorkteamForLabeling"
        ]
        self.use_private_workteam_for_verification = config_yaml[
            "usePrivateWorkteamForVerification"
        ]
        self.verification_job_private_workteam_arn = config_yaml[
            "verificationJobPrivateWorkteamArn"
        ]
        self.max_labels_per_labeling_job = config_yaml["maxLabelsPerLabelingJob"]
        self.labeling_pipeline_schedule = config_yaml["labelingPipelineSchedule"]
        self.feature_group_name = config_yaml["featureGroupName"]
        # self.assets_bucket= str(config_yaml['assets_bucket'])
        self.model_package_group_name = config_yaml["modelPackageGroupName"]
        self.model_package_group_description = config_yaml[
            "modelPackageGroupDescription"
        ]
        # self.feature_group_name=str(cdk.Fn.import_value("aiopsfeatureGroup")),
        # self.assets_bucket=str(cdk.Fn.import_value("aiopsDataBucket")),


# class LabelingPipelineStack(Stack):
#    def __init__(self, scope: Construct, construct_id: str, app_config: AppConfig, **kwargs) -> None:
#        super().__init__(scope, construct_id, **kwargs)

# Define your labeling pipeline resources here


def add_security_checks(app: cdk.App, stacks: list[Stack]):
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


def main():
    app_config = AppConfig(app, "aiops-config")
    init_stack = InitStack(app, "aiops-init-stack", app_config)
    labeling_pipeline_stack = LabelingPipelineStack(
        app, "aiops-labeling-infra-stack", app_config
    )
    # Add the dependency
    labeling_pipeline_stack.add_dependency(init_stack)

    # Statemachine stack
    statemachine_pipeline_stack = ExecuteStateMachinePipeline(
        app, "aiops-statemachine-pipeline", app_config
    )
    statemachine_pipeline_stack.add_dependency(init_stack)
    statemachine_pipeline_stack.add_dependency(labeling_pipeline_stack)

    add_security_checks(
        app, [init_stack, labeling_pipeline_stack, statemachine_pipeline_stack]
    )
    app.synth()


if __name__ == "__main__":
    main()
