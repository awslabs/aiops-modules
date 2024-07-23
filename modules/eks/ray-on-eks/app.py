# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_cdk import App, CfnOutput, Environment, Tags

from ray_stack import RayOnEKS
from rbac_stack import RbacStack
from settings import ApplicationSettings

app_settings = ApplicationSettings()

app = App()
env = Environment(
    account=app_settings.default.account,
    region=app_settings.default.region,
)

rbac_stack = RbacStack(
    scope=app,
    id=f"{app_settings.settings.app_prefix}-rbac",
    project_name=app_settings.settings.project_name,
    deployment_name=app_settings.settings.deployment_name,
    module_name=app_settings.settings.module_name,
    eks_cluster_name=app_settings.parameters.eks_cluster_name,
    eks_admin_role_arn=app_settings.parameters.eks_cluster_admin_role_arn,
    eks_oidc_arn=app_settings.parameters.eks_oidc_arn,
    eks_openid_issuer=app_settings.parameters.eks_openid_issuer,
    namespace_name=app_settings.parameters.namespace,
    env=env,
)

ray_on_eks_stack = RayOnEKS(
    scope=app,
    id=app_settings.settings.app_prefix,
    project_name=app_settings.settings.project_name,
    deployment_name=app_settings.settings.deployment_name,
    module_name=app_settings.settings.module_name,
    eks_cluster_name=app_settings.parameters.eks_cluster_name,
    eks_admin_role_arn=app_settings.parameters.eks_cluster_admin_role_arn,
    eks_openid_connect_provider_arn=app_settings.parameters.eks_oidc_arn,
    eks_cluster_endpoint=app_settings.parameters.eks_cluster_endpoint,
    eks_cert_auth_data=app_settings.parameters.eks_cert_auth_data,
    namespace_name=app_settings.parameters.namespace,
    service_account_name=rbac_stack.service_account.service_account_name,
    service_account_role=rbac_stack.service_account.role,
    env=env,
)

if app_settings.parameters.tags:
    for tag_key, tag_value in app_settings.parameters.tags.items():
        Tags.of(app).add(tag_key, tag_value)

Tags.of(app).add("SeedFarmerDeploymentName", app_settings.settings.deployment_name)
Tags.of(app).add("SeedFarmerModuleName", app_settings.settings.module_name)
Tags.of(app).add("SeedFarmerProjectName", app_settings.settings.project_name)

CfnOutput(
    scope=ray_on_eks_stack,
    id="metadata",
    value=rbac_stack.to_json_string(
        {
            "EksServiceAccountName": rbac_stack.service_account.service_account_name,
            "EksServiceAccountRoleArn": rbac_stack.service_account.role.role_arn,
            "NamespaceName": app_settings.parameters.namespace,
        }
    ),
)

app.synth(force=True)
