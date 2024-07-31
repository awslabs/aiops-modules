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
def ray_cluster_stack(stack_defaults) -> cdk.Stack:
    import ray_cluster_stack

    app = cdk.App()

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    eks_cluster_name = "cluster"
    eks_cluster_admin_role_arn = "arn:aws:iam::123456789012:role/eks-testing-XXXXXX"
    eks_oidc_arn = "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/XXXXXXXX"
    namespace = "namespace"
    service_account_name = "acc"
    ray_version = "2.23.0"
    ray_cluster_helm_chart_version = "1.1.1"
    image_uri = "img:latest"
    enable_autoscaling = True
    autoscaler_idle_timeout_seconds = 60
    worker_replicas = 1
    worker_min_replicas = 4
    worker_max_replicas = 10
    head_resources = {"limits": {"cpu": "1", "memory": "8G"}, "requests": {"cpu": "1", "memory": "8G"}}
    worker_resources = {"limits": {"cpu": "1", "memory": "8G"}, "requests": {"cpu": "1", "memory": "8G"}}
    worker_tolerations = []
    worker_labels = {}
    pvc_name = "pvc"
    dra_export_path = "/ray/export"

    return ray_cluster_stack.RayCluster(
        scope=app,
        id=app_prefix,
        project_name=project_name,
        deployment_name=dep_name,
        module_name=mod_name,
        eks_cluster_name=eks_cluster_name,
        eks_admin_role_arn=eks_cluster_admin_role_arn,
        eks_openid_connect_provider_arn=eks_oidc_arn,
        namespace_name=namespace,
        service_account_name=service_account_name,
        ray_version=ray_version,
        ray_cluster_helm_chart_version=ray_cluster_helm_chart_version,
        image_uri=image_uri,
        enable_autoscaling=enable_autoscaling,
        autoscaler_idle_timeout_seconds=autoscaler_idle_timeout_seconds,
        head_resources=head_resources,
        worker_replicas=worker_replicas,
        worker_min_replicas=worker_min_replicas,
        worker_max_replicas=worker_max_replicas,
        worker_resources=worker_resources,
        worker_tolerations=worker_tolerations,
        worker_labels=worker_labels,
        pvc_name=pvc_name,
        dra_export_path=dra_export_path,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )


def test_synthesize_ray_stack(ray_cluster_stack: cdk.Stack) -> None:
    template = Template.from_stack(ray_cluster_stack)
    template.resource_count_is("Custom::AWSCDK-EKS-HelmChart", 1)
