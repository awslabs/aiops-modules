# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_cdk import App, CfnOutput, Environment, Tags

from ray_cluster_stack import RayCluster
from settings import ApplicationSettings

app_settings = ApplicationSettings()

app = App()
env = Environment(
    account=app_settings.default.account,
    region=app_settings.default.region,
)

ray_cluster_stack = RayCluster(
    scope=app,
    id=app_settings.settings.app_prefix,
    project_name=app_settings.settings.project_name,
    deployment_name=app_settings.settings.deployment_name,
    module_name=app_settings.settings.module_name,
    eks_cluster_name=app_settings.parameters.eks_cluster_name,
    eks_admin_role_arn=app_settings.parameters.eks_cluster_admin_role_arn,
    eks_openid_connect_provider_arn=app_settings.parameters.eks_oidc_arn,
    namespace_name=app_settings.parameters.namespace,
    service_account_name=app_settings.parameters.service_account_name,
    ray_version=app_settings.parameters.ray_version,
    ray_cluster_helm_chart_version=app_settings.parameters.ray_cluster_helm_chart_version,
    image_uri=app_settings.parameters.image_uri,
    enable_autoscaling=app_settings.parameters.enable_autoscaling,
    autoscaler_idle_timeout_seconds=app_settings.parameters.autoscaler_idle_timeout_seconds,
    head_resources=app_settings.parameters.head_resources,
    worker_replicas=app_settings.parameters.worker_replicas,
    worker_min_replicas=app_settings.parameters.worker_min_replicas,
    worker_max_replicas=app_settings.parameters.worker_max_replicas,
    worker_resources=app_settings.parameters.worker_resources,
    worker_tolerations=app_settings.parameters.worker_tolerations,
    pvc_name=app_settings.parameters.pvc_name,
    dra_export_path=app_settings.parameters.dra_export_path,
    env=env,
)

if app_settings.parameters.tags:
    for tag_key, tag_value in app_settings.parameters.tags.items():
        Tags.of(app).add(tag_key, tag_value)

Tags.of(app).add("SeedFarmerDeploymentName", app_settings.settings.deployment_name)
Tags.of(app).add("SeedFarmerModuleName", app_settings.settings.module_name)
Tags.of(app).add("SeedFarmerProjectName", app_settings.settings.project_name)

CfnOutput(
    scope=ray_cluster_stack,
    id="metadata",
    value=ray_cluster_stack.to_json_string(
        {
            "NamespaceName": app_settings.parameters.namespace,
        }
    ),
)

app.synth(force=True)
