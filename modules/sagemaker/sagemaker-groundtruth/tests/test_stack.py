import pytest
import yaml
from aws_cdk import App
from typing import Any
from aws_cdk.assertions import Template
from lib.stacks.init import LabelingInitStack
from lib.stacks.labeling_pipeline import LabelingPipelineStack
from lib.stacks.statemachine_pipeline import ExecuteStateMachinePipeline


@pytest.fixture
def app_config() -> dict[str, Any]:
    with open("config.yaml") as file:
        config_yaml = yaml.safe_load(file)
    with open("repo_config.yaml") as repo_file:
        repo_config_yaml = yaml.safe_load(repo_file)

    config = {
        "repo_type": repo_config_yaml["repoType"],
        "repo_name": repo_config_yaml["repoName"],
        "branch_name": repo_config_yaml["branchName"],
        "github_repo_owner": repo_config_yaml["githubRepoOwner"],
        "github_connection_arn": repo_config_yaml["githubConnectionArn"],
        "pipeline_assets_prefix": config_yaml["pipelineAssetsPrefix"],
        "labeling_job_private_workteam_arn": config_yaml[
            "labelingJobPrivateWorkteamArn"
        ],
        "use_private_workteam_for_labeling": config_yaml[
            "usePrivateWorkteamForLabeling"
        ],
        "use_private_workteam_for_verification": config_yaml[
            "usePrivateWorkteamForVerification"
        ],
        "verification_job_private_workteam_arn": config_yaml[
            "verificationJobPrivateWorkteamArn"
        ],
        "max_labels_per_labeling_job": config_yaml["maxLabelsPerLabelingJob"],
        "labeling_pipeline_schedule": config_yaml["labelingPipelineSchedule"],
        "feature_group_name": config_yaml["featureGroupName"],
        "model_package_group_name": config_yaml["modelPackageGroupName"],
        "model_package_group_description": config_yaml["modelPackageGroupDescription"],
    }

    return config


def test_init_stack(app_config: dict[str, Any]) -> None:
    app = App()
    init_stack = LabelingInitStack(
        app,
        "aiops-init-stack",
        app_config["repo_name"],
        app_config["branch_name"],
        app_config["repo_type"],
        app_config["model_package_group_name"],
        app_config["model_package_group_description"],
        app_config,
    )

    template = Template.from_stack(init_stack)

    # Test if the CodeCommit repository is created (if repo_type is CODECOMMIT)
    if app_config["repo_type"] == "CODECOMMIT":
        template.resource_count_is("AWS::CodeCommit::Repository", 1)
        template.has_resource_properties(
            "AWS::CodeCommit::Repository",
            {
                "RepositoryName": app_config["repo_name"],
            },
        )
    # Test if the S3 bucket is created
    template.resource_count_is("AWS::S3::Bucket", 1)

    # Test if the IAM role for seeding assets is created
    template.resource_count_is("AWS::IAM::Role", 4)

    # Test if the Lambda function for seeding labels is created
    template.resource_count_is("AWS::Lambda::Function", 4)

    # Test if the SageMaker Feature Group is created
    template.resource_count_is("AWS::SageMaker::FeatureGroup", 1)

    # Test if the SageMaker Model Package Group is created
    template.resource_count_is("AWS::SageMaker::ModelPackageGroup", 1)


def test_labeling_pipeline_stack(app_config: dict[str, Any]) -> None:
    app = App()
    labeling_pipeline_stack = LabelingPipelineStack(
        app, "aiops-labeling-infra-stack", app_config
    )

    template = Template.from_stack(labeling_pipeline_stack)

    # Test if the CodeBuild project resources are created
    template.resource_count_is("AWS::CodeBuild::Project", 7)

    template.resource_count_is("AWS::CodePipeline::Pipeline", 1)

    # Test if the scheduled event rule is created correctly
    template.resource_count_is("AWS::Events::Rule", 2)


def test_statemachine_pipeline_stack(app_config: dict[str, Any]) -> None:
    app = App()
    statemachine_pipeline_stack = ExecuteStateMachinePipeline(
        app, "aiops-statemachine-pipeline", app_config
    )

    template = Template.from_stack(statemachine_pipeline_stack)

    # Test if the StateMachine resource is created
    template.resource_count_is("AWS::StepFunctions::StateMachine", 1)

    # Test if the required Lambda functions are created
    template.resource_count_is("AWS::Lambda::Function", 4)

    template.resource_count_is("AWS::CodePipeline::Pipeline", 1)

    template.resource_count_is("AWS::StepFunctions::StateMachine", 1)
