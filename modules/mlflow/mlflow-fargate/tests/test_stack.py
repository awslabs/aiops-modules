import os
import sys
from unittest import mock

import aws_cdk as cdk
import cdk_nag
import pytest
from aws_cdk.assertions import Annotations, Match, Template


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
def stack(stack_defaults, use_rds: bool) -> cdk.Stack:
    import stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    vpc_id = "vpc-123"
    subnet_ids = []
    ecr_repo_name = "repo"
    task_cpu_units = 4 * 1024
    task_memory_limit_mb = 8 * 1024
    autoscale_max_capacity = 2
    artifacts_bucket_name = "bucket"
    efs_removal_policy = "DESTROY"

    if use_rds:
        rds_settings = {
            "hostname": "hostname",
            "port": 3306,
            "security_group_id": "sg-01234",
            "credentials_secret_arn": "arn:aws:secretsmanager:us-east-1:111111111111:secret:xxxxxx/xxxxxx-yyyyyy",
        }
    else:
        rds_settings = None

    return stack.MlflowFargateStack(
        scope=app,
        id=app_prefix,
        vpc_id=vpc_id,
        subnet_ids=subnet_ids,
        ecs_cluster_name=None,
        service_name=None,
        ecr_repo_name=ecr_repo_name,
        task_cpu_units=task_cpu_units,
        task_memory_limit_mb=task_memory_limit_mb,
        autoscale_max_capacity=autoscale_max_capacity,
        artifacts_bucket_name=artifacts_bucket_name,
        rds_settings=rds_settings,
        lb_access_logs_bucket_name=None,
        lb_access_logs_bucket_prefix=None,
        efs_removal_policy=efs_removal_policy,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )


@pytest.mark.parametrize("use_rds", [False, True])
def test_synthesize_stack(stack: cdk.Stack, use_rds: bool) -> None:
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::ECS::Cluster", 1)
    template.resource_count_is("AWS::ECS::TaskDefinition", 1)


@pytest.mark.parametrize("use_rds", [False, True])
def test_no_cdk_nag_errors(stack: cdk.Stack, use_rds: bool) -> None:
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
