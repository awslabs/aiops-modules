import os
import sys
from unittest import mock

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template


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
def rbac_stack(stack_defaults) -> cdk.Stack:
    import rbac_stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    eks_cluster_name = "cluster"
    eks_cluster_admin_role_arn = "arn:aws:iam::123456789012:role/eks-testing-XXXXXX"
    eks_oidc_arn = "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/XXXXXXXX"
    eks_openid_issuer = "sts.amazon.com"
    eks_handler_role_arn = "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/YYYYYYYY"
    namespace = "namespace"
    data_bucket_name = "bucket"

    return rbac_stack.RbacStack(
        scope=app,
        id=f"{app_prefix}-rbac",
        project_name=project_name,
        deployment_name=dep_name,
        module_name=mod_name,
        eks_cluster_name=eks_cluster_name,
        eks_admin_role_arn=eks_cluster_admin_role_arn,
        eks_oidc_arn=eks_oidc_arn,
        eks_openid_issuer=eks_openid_issuer,
        eks_handler_role_arn=eks_handler_role_arn,
        namespace_name=namespace,
        data_bucket_name=data_bucket_name,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )


@pytest.fixture(scope="function")
def ray_stack(rbac_stack, stack_defaults) -> cdk.Stack:
    import ray_stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    eks_cluster_name = "cluster"
    eks_cluster_admin_role_arn = "arn:aws:iam::123456789012:role/eks-testing-XXXXXX"
    eks_handler_role_arn = "arn:aws:iam::123456789012:role/eks-testing-XXXXXX"
    eks_oidc_arn = "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/XXXXXXXX"
    eks_cluster_endpoint = "oidc.eks.us-west-2.amazonaws.com/id/XXXXXXXXXX"
    eks_cert_auth_data = "auth"
    namespace = "namespace"

    return ray_stack.RayOnEKS(
        scope=app,
        id=f"{app_prefix}-ray",
        project_name=project_name,
        deployment_name=dep_name,
        module_name=mod_name,
        eks_cluster_name=eks_cluster_name,
        eks_admin_role_arn=eks_cluster_admin_role_arn,
        eks_handler_role_arn=eks_handler_role_arn,
        eks_openid_connect_provider_arn=eks_oidc_arn,
        eks_cluster_endpoint=eks_cluster_endpoint,
        eks_cert_auth_data=eks_cert_auth_data,
        namespace_name=namespace,
        service_account_name=rbac_stack.service_account.service_account_name,
        service_account_role=rbac_stack.service_account.role,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )


def test_synthesize_rbac_stack(rbac_stack: cdk.Stack) -> None:
    template = Template.from_stack(rbac_stack)
    template.resource_count_is("AWS::IAM::Role", 2)


def test_synthesize_ray_stack(ray_stack: cdk.Stack) -> None:
    template = Template.from_stack(ray_stack)
    template.resource_count_is("Custom::AWSCDK-EKS-HelmChart", 1)
