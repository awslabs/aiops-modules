# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import cast

from aws_cdk import App, CfnOutput, Environment

from rbac_stack import RbacStack
from ray_stack import RayOnEKS

# Project specific
project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")
app_prefix = f"{project_name}-{deployment_name}-{module_name}"


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


eks_cluster_name = cast(str, os.getenv(_param("EKS_CLUSTER_NAME")))
eks_admin_role_arn = cast(str, os.getenv(_param("EKS_CLUSTER_ADMIN_ROLE_ARN")))
eks_oidc_provider_arn = cast(str, os.getenv(_param("EKS_OIDC_ARN")))
eks_openid_issuer = cast(str, os.getenv(_param("EKS_OPENID_ISSUER")))
eks_cluster_endpoint = cast(str, os.getenv(_param("EKS_CLUSTER_ENDPOINT")))
eks_cert_auth_data = cast(str, os.getenv(_param("EKS_CERT_AUTH_DATA")))
namespace = cast(str, os.getenv(_param("NAMESPACE")))
ray_image_uri = os.getenv(_param("RAY_IMAGE_URI"))

app = App()
env = Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

rbac_stack = RbacStack(
    scope=app,
    id=f"{app_prefix}-rbac",
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    eks_cluster_name=eks_cluster_name,
    eks_admin_role_arn=eks_admin_role_arn,
    eks_oidc_arn=eks_oidc_provider_arn,
    eks_openid_issuer=eks_openid_issuer,
    namespace_name=namespace,
    env=env,
)

ray_on_eks_stack = RayOnEKS(
    scope=app,
    id=f"{app_prefix}-ray",
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    eks_cluster_name=eks_cluster_name,
    eks_admin_role_arn=eks_admin_role_arn,
    eks_openid_connect_provider_arn=eks_oidc_provider_arn,
    eks_cluster_endpoint=eks_cluster_endpoint,
    eks_cert_auth_data=eks_cert_auth_data,
    namespace_name=namespace,
    service_account_role=rbac_stack.service_account_role,
    ray_image_uri=ray_image_uri,
    env=env,
)

CfnOutput(
    scope=rbac_stack,
    id="metadata",
    value=rbac_stack.to_json_string(
        {
            "EksServiceAccountRoleArn": rbac_stack.service_account_role.role_arn,
            "NamespaceName": namespace,
        }
    ),
)

app.synth(force=True)
