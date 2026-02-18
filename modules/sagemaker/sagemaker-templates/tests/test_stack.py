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
    dev_account_id = "dev_account_id"
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
            enable_manual_approval=True,
            enable_eventbridge_trigger=True,
            enable_data_capture=True,
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
        dev_account_id=dev_account_id,
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
        permissions_boundary_name=None,
        s3_access_logs_bucket_arn=None,
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


@pytest.fixture(scope="function")
def stack_with_logging(stack_defaults, project_template_type) -> cdk.Stack:
    import stack

    app = cdk.App()

    xgboost_abalone_settings = None
    batch_inference_settings = None

    if project_template_type == ProjectTemplateType.XGBOOST_ABALONE:
        xgboost_abalone_settings = XGBoostAbaloneProjectSettings(
            enable_network_isolation="False", encrypt_inter_container_traffic="False"
        )
    elif project_template_type == ProjectTemplateType.BATCH_INFERENCE:
        batch_inference_settings = BatchInferenceProjectSettings(
            model_package_group_name="test-model-package-group",
            model_bucket_name="test-model-bucket",
            base_job_prefix="test-job-prefix",
        )

    return stack.ProjectStack(
        app,
        "test-logging-stack",
        project_template_type=project_template_type,
        sagemaker_project_name="xgboost-1",
        sagemaker_project_id="xgboost-1",
        dev_account_id="dev_account_id",
        dev_vpc_id="",
        dev_subnet_ids=[],
        dev_security_group_ids=[],
        pre_prod_account_id="pre_prod_account_id",
        pre_prod_region="us-east-1",
        pre_prod_vpc_id="",
        pre_prod_subnet_ids=[],
        pre_prod_security_group_ids=[],
        prod_account_id="prod_account_id",
        prod_region="us-east-1",
        prod_vpc_id="",
        prod_subnet_ids=[],
        prod_security_group_ids=[],
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
        sagemaker_domain_id="domain_id",
        sagemaker_domain_arn="arn:aws:sagemaker:::domain/domain_id",
        repository_type=RepositoryType.CODECOMMIT,
        access_token_secret_name=None,
        aws_codeconnection_arn=None,
        repository_owner=None,
        xgboost_abalone_project_settings=xgboost_abalone_settings,
        model_deploy_project_settings=None,
        hf_import_models_project_settings=None,
        batch_inference_project_settings=batch_inference_settings,
        permissions_boundary_name=None,
        s3_access_logs_bucket_arn="arn:aws:s3:::test-access-logs-bucket",
    )


@pytest.mark.parametrize(
    "project_template_type",
    [
        ProjectTemplateType.XGBOOST_ABALONE,
        ProjectTemplateType.BATCH_INFERENCE,
    ],
    indirect=True,
)
def test_s3_access_logging_configured(stack_with_logging: cdk.Stack, project_template_type) -> None:
    """Test that S3 buckets have logging configuration when s3_access_logs_bucket_arn is provided."""
    from aws_cdk.assertions import Template

    template = Template.from_stack(stack_with_logging)
    buckets = template.find_resources("AWS::S3::Bucket")

    expected_count = {
        ProjectTemplateType.XGBOOST_ABALONE: 2,
        ProjectTemplateType.BATCH_INFERENCE: 1,
    }[project_template_type]

    buckets_with_logging = []
    for logical_id, resource in buckets.items():
        props = resource.get("Properties", {})
        logging_config = props.get("LoggingConfiguration", {})
        if logging_config:
            prefix = logging_config.get("LogFilePrefix", "")
            assert prefix, f"Bucket {logical_id} has empty log prefix"
            assert "xgboost-1" in prefix, f"Bucket {logical_id} log prefix missing project name: {prefix}"
            buckets_with_logging.append(logical_id)

    assert (
        len(buckets_with_logging) == expected_count
    ), f"Expected {expected_count} buckets with logging, found {len(buckets_with_logging)}: {buckets_with_logging}"


@pytest.mark.parametrize(
    "project_template_type",
    [
        ProjectTemplateType.XGBOOST_ABALONE,
        ProjectTemplateType.BATCH_INFERENCE,
    ],
    indirect=True,
)
def test_no_cdk_nag_errors_with_logging(stack_with_logging: cdk.Stack, project_template_type) -> None:
    """Test that CDK Nag passes when S3 access logging is configured."""
    cdk.Aspects.of(stack_with_logging).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack_with_logging).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors with logging enabled"


@pytest.fixture(scope="function")
def stack_single_account(stack_defaults, project_template_type) -> cdk.Stack:
    import stack

    app = cdk.App()
    same_account_id = os.environ["CDK_DEFAULT_ACCOUNT"]
    sagemaker_domain_id = "domain_id"

    xgboost_abalone_settings = None
    hf_import_models_settings = None

    if project_template_type == ProjectTemplateType.XGBOOST_ABALONE:
        xgboost_abalone_settings = XGBoostAbaloneProjectSettings(
            enable_network_isolation="False", encrypt_inter_container_traffic="False"
        )
    elif project_template_type == ProjectTemplateType.HF_IMPORT_MODELS:
        hf_import_models_settings = HfImportModelsProjectSettings(
            hf_access_token_secret="test-hf-token-secret", hf_model_id="test-model-id"
        )

    return stack.ProjectStack(
        app,
        "test-single-account-stack",
        project_template_type=project_template_type,
        sagemaker_project_name="test-project",
        sagemaker_project_id="test-project-id",
        dev_account_id=same_account_id,
        dev_vpc_id="",
        dev_subnet_ids=[],
        dev_security_group_ids=[],
        pre_prod_account_id=same_account_id,
        pre_prod_region="us-east-1",
        pre_prod_vpc_id="",
        pre_prod_subnet_ids=[],
        pre_prod_security_group_ids=[],
        prod_account_id=same_account_id,
        prod_region="us-east-1",
        prod_vpc_id="",
        prod_subnet_ids=[],
        prod_security_group_ids=[],
        env=cdk.Environment(
            account=same_account_id,
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
        sagemaker_domain_id=sagemaker_domain_id,
        sagemaker_domain_arn=f"arn:aws:sagemaker:::domain/{sagemaker_domain_id}",
        repository_type=RepositoryType.CODECOMMIT,
        access_token_secret_name=None,
        aws_codeconnection_arn=None,
        repository_owner=None,
        xgboost_abalone_project_settings=xgboost_abalone_settings,
        model_deploy_project_settings=None,
        hf_import_models_project_settings=hf_import_models_settings,
        batch_inference_project_settings=None,
        permissions_boundary_name=None,
        s3_access_logs_bucket_arn=None,
    )


@pytest.mark.parametrize(
    "project_template_type",
    [
        ProjectTemplateType.XGBOOST_ABALONE,
        ProjectTemplateType.FINETUNE_LLM_EVALUATION,
        ProjectTemplateType.HF_IMPORT_MODELS,
    ],
    indirect=True,
)
def test_no_duplicate_principals_in_model_package_group_policy(
    stack_single_account: cdk.Stack, project_template_type
) -> None:
    """Test that single-account deployments don't create duplicate principals.

    When all account IDs (dev, pre-prod, prod) are the same, the policy should
    deduplicate them to avoid SageMaker's "Duplicate principal" validation error.

    This test checks each policy statement individually, as SageMaker rejects
    policies where the same principal appears multiple times within a single statement.
    """
    import json

    from aws_cdk.assertions import Template

    def stringify_principal(principal) -> str:
        """Convert a principal to a comparable string representation."""
        if isinstance(principal, str):
            return principal
        elif isinstance(principal, dict):
            # Handle Fn::Join and other intrinsic functions
            return json.dumps(principal, sort_keys=True)
        return str(principal)

    def check_statement_for_duplicates(statement: dict, logical_id: str, statement_sid: str) -> None:
        """Check a single policy statement for duplicate principals."""
        principal = statement.get("Principal", {})
        if isinstance(principal, dict):
            aws_principals = principal.get("AWS", [])
            if isinstance(aws_principals, list):
                principal_strs = [stringify_principal(p) for p in aws_principals]
                assert len(principal_strs) == len(
                    set(principal_strs)
                ), f"Duplicate principals in {logical_id} statement '{statement_sid}': {aws_principals}"

    template = Template.from_stack(stack_single_account)
    model_package_groups = template.find_resources("AWS::SageMaker::ModelPackageGroup")

    assert model_package_groups, "Expected at least one ModelPackageGroup resource"

    for logical_id, resource in model_package_groups.items():
        policy = resource.get("Properties", {}).get("ModelPackageGroupPolicy")
        if policy:
            if isinstance(policy, str):
                policy = json.loads(policy)

            if isinstance(policy, dict):
                for statement in policy.get("Statement", []):
                    statement_sid = statement.get("Sid", "unknown")
                    check_statement_for_duplicates(statement, logical_id, statement_sid)


@pytest.mark.parametrize(
    "project_template_type",
    [
        ProjectTemplateType.XGBOOST_ABALONE,
        ProjectTemplateType.FINETUNE_LLM_EVALUATION,
        ProjectTemplateType.HF_IMPORT_MODELS,
    ],
    indirect=True,
)
def test_no_duplicate_principals_in_kms_key_policy(stack_single_account: cdk.Stack, project_template_type) -> None:
    """Test that single-account deployments don't create duplicate principals in KMS key policies.

    When pre-prod and prod account IDs are the same, the KMS key policy should
    deduplicate them to avoid "Duplicate principal" validation errors.
    """
    import json

    from aws_cdk.assertions import Template

    def stringify_principal(principal) -> str:
        """Convert a principal to a comparable string representation."""
        if isinstance(principal, str):
            return principal
        elif isinstance(principal, dict):
            return json.dumps(principal, sort_keys=True)
        return str(principal)

    def check_statement_for_duplicates(statement: dict, logical_id: str, statement_sid: str) -> None:
        """Check a single policy statement for duplicate principals."""
        principal = statement.get("Principal", {})
        if isinstance(principal, dict):
            aws_principals = principal.get("AWS", [])
            if isinstance(aws_principals, list):
                principal_strs = [stringify_principal(p) for p in aws_principals]
                assert len(principal_strs) == len(
                    set(principal_strs)
                ), f"Duplicate principals in KMS key {logical_id} statement '{statement_sid}': {aws_principals}"

    template = Template.from_stack(stack_single_account)
    kms_keys = template.find_resources("AWS::KMS::Key")

    assert kms_keys, "Expected at least one KMS Key resource"

    for logical_id, resource in kms_keys.items():
        policy = resource.get("Properties", {}).get("KeyPolicy")
        if policy:
            if isinstance(policy, str):
                policy = json.loads(policy)

            if isinstance(policy, dict):
                for statement in policy.get("Statement", []):
                    statement_sid = statement.get("Sid", "unknown")
                    check_statement_for_duplicates(statement, logical_id, statement_sid)


@pytest.mark.parametrize(
    "project_template_type",
    [
        ProjectTemplateType.XGBOOST_ABALONE,
        ProjectTemplateType.FINETUNE_LLM_EVALUATION,
        ProjectTemplateType.HF_IMPORT_MODELS,
    ],
    indirect=True,
)
def test_no_duplicate_principals_in_s3_bucket_policy(stack_single_account: cdk.Stack, project_template_type) -> None:
    """Test that single-account deployments don't create duplicate principals in S3 bucket policies.

    When pre-prod and prod account IDs are the same, the S3 bucket policy should
    deduplicate them to avoid "Duplicate principal" validation errors.
    """
    import json

    from aws_cdk.assertions import Template

    def stringify_principal(principal) -> str:
        """Convert a principal to a comparable string representation."""
        if isinstance(principal, str):
            return principal
        elif isinstance(principal, dict):
            return json.dumps(principal, sort_keys=True)
        return str(principal)

    def check_statement_for_duplicates(statement: dict, logical_id: str, statement_sid: str) -> None:
        """Check a single policy statement for duplicate principals."""
        principal = statement.get("Principal", {})
        if isinstance(principal, dict):
            aws_principals = principal.get("AWS", [])
            if isinstance(aws_principals, list):
                principal_strs = [stringify_principal(p) for p in aws_principals]
                assert len(principal_strs) == len(set(principal_strs)), (
                    f"Duplicate principals in S3 bucket policy {logical_id} "
                    f"statement '{statement_sid}': {aws_principals}"
                )

    template = Template.from_stack(stack_single_account)
    bucket_policies = template.find_resources("AWS::S3::BucketPolicy")

    assert bucket_policies, "Expected at least one S3 BucketPolicy resource"

    for logical_id, resource in bucket_policies.items():
        policy = resource.get("Properties", {}).get("PolicyDocument")
        if policy:
            if isinstance(policy, str):
                policy = json.loads(policy)

            if isinstance(policy, dict):
                for statement in policy.get("Statement", []):
                    statement_sid = statement.get("Sid", "unknown")
                    check_statement_for_duplicates(statement, logical_id, statement_sid)
