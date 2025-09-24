# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys
from unittest import mock

import aws_cdk as cdk
import cdk_nag
import pytest
from aws_cdk.assertions import Annotations, Match

from settings import (
    BatchInferenceProjectSettings,
    HfImportModelsProjectSettings,
    ModelDeployProjectSettings,
    ProjectTemplateType,
    RepositoryType,
    XGBoostAbaloneProjectSettings,
)


@pytest.fixture(scope="function")
def stack_defaults():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
        os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

        # Unload the app import so that subsequent tests don't reuse

        if "stack" in sys.modules:
            del sys.modules["stack"]

        yield


@pytest.fixture(scope="function")
def project_template_type(request):
    """Fixture to provide project template type from parametrize."""
    return request.param


@pytest.fixture(scope="function")
def stack(stack_defaults, project_template_type) -> cdk.Stack:
    import stack

    app = cdk.App()
    sagemaker_project_name = "xgboost-1"
    sagemaker_project_id = "xgboost-1"
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    dev_vpc_id = "vpc"
    dev_subnet_ids = ["sub"]
    dev_security_group_ids = ["sg"]
    pre_prod_account_id = "pre_prod_account_id"
    pre_prod_region = "us-east-1"
    pre_prod_vpc_id = "vpc"
    pre_prod_subnet_ids = ["sub"]
    pre_prod_security_group_ids = ["sg"]
    prod_account_id = "prod_account_id"
    prod_region = "us-east-1"
    prod_vpc_id = "vpc"
    prod_subnet_ids = ["sub"]
    prod_security_group_ids = ["sg"]
    sagemaker_domain_id = "domain_id"
    sagemaker_domain_arn = f"arn:aws:sagemaker:::domain/{sagemaker_domain_id}"
    repository_type = RepositoryType.CODECOMMIT
    access_token_secret_name = "github_token"
    aws_codeconnection_arn = (
        "arn:aws:codeconnections:xxxxxx:xxxxxxxxxxxx:connection/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    )
    repository_owner = "github-test-owner"

    # Create mock settings objects for each template type
    xgboost_abalone_settings = None
    model_deploy_settings = None
    hf_import_models_settings = None
    batch_inference_settings = None

    if project_template_type == ProjectTemplateType.XGBOOST_ABALONE:
        xgboost_abalone_settings = XGBoostAbaloneProjectSettings(
            enable_network_isolation="False", encrypt_inter_container_traffic="False"
        )
    elif project_template_type == ProjectTemplateType.MODEL_DEPLOY:
        model_deploy_settings = ModelDeployProjectSettings(
            model_package_group_name="test-model-package-group",
            model_bucket_name="test-model-bucket",
            enable_network_isolation="false",
        )
    elif project_template_type == ProjectTemplateType.HF_IMPORT_MODELS:
        hf_import_models_settings = HfImportModelsProjectSettings(
            hf_access_token_secret="test-hf-token-secret", hf_model_id="test-model-id"
        )
    elif project_template_type == ProjectTemplateType.BATCH_INFERENCE:
        batch_inference_settings = BatchInferenceProjectSettings(
            model_package_group_name="test-model-package-group",
            model_bucket_name="test-model-bucket",
            base_job_prefix="test-job-prefix",
        )

    return stack.ProjectStack(
        app,
        f"{project_name}-{dep_name}-{mod_name}",
        project_template_type=project_template_type,
        sagemaker_project_name=sagemaker_project_name,
        sagemaker_project_id=sagemaker_project_id,
        dev_vpc_id=dev_vpc_id,
        dev_subnet_ids=dev_subnet_ids,
        dev_security_group_ids=dev_security_group_ids,
        pre_prod_account_id=pre_prod_account_id,
        pre_prod_region=pre_prod_region,
        pre_prod_vpc_id=pre_prod_vpc_id,
        pre_prod_subnet_ids=pre_prod_subnet_ids,
        pre_prod_security_group_ids=pre_prod_security_group_ids,
        prod_account_id=prod_account_id,
        prod_region=prod_region,
        prod_vpc_id=prod_vpc_id,
        prod_subnet_ids=prod_subnet_ids,
        prod_security_group_ids=prod_security_group_ids,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
        sagemaker_domain_id=sagemaker_domain_id,
        sagemaker_domain_arn=sagemaker_domain_arn,
        repository_type=repository_type,
        access_token_secret_name=access_token_secret_name,
        aws_codeconnection_arn=aws_codeconnection_arn,
        repository_owner=repository_owner,
        xgboost_abalone_project_settings=xgboost_abalone_settings,
        model_deploy_project_settings=model_deploy_settings,
        hf_import_models_project_settings=hf_import_models_settings,
        batch_inference_project_settings=batch_inference_settings,
    )


@pytest.mark.parametrize(
    "project_template_type",
    [
        ProjectTemplateType.XGBOOST_ABALONE,
        ProjectTemplateType.BATCH_INFERENCE,
        ProjectTemplateType.FINETUNE_LLM_EVALUATION,
        ProjectTemplateType.HF_IMPORT_MODELS,
        ProjectTemplateType.MODEL_DEPLOY,
    ],
    indirect=True,
)
def test_no_cdk_nag_errors(stack: cdk.Stack, project_template_type) -> None:
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
