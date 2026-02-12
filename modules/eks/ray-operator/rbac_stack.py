# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Optional, cast

from aws_cdk import Stack, Tags
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk.lambda_layer_kubectl_v29 import KubectlV29Layer
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class RbacStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        project_name: str,
        deployment_name: str,
        module_name: str,
        eks_cluster_name: str,
        eks_admin_role_arn: str,
        eks_oidc_arn: str,
        eks_openid_issuer: str,
        eks_handler_role_arn: str,
        namespace_name: str,
        data_bucket_name: Optional[str],
        permissions_boundary_name: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.project_name = project_name
        self.deployment_name = deployment_name
        self.module_name = module_name
        self.namespace_name = namespace_name

        super().__init__(
            scope,
            id,
            description="This stack deploys EKS RBAC Configuration",
            **kwargs,
        )

        # Apply permissions boundary to all roles in this stack if provided
        if permissions_boundary_name:
            permissions_boundary_policy = iam.ManagedPolicy.from_managed_policy_name(
                self, "PermBoundary", permissions_boundary_name
            )
            iam.PermissionsBoundary.of(self).apply(permissions_boundary_policy)

        dep_mod = f"{project_name}-{deployment_name}-{module_name}"
        # used to tag AWS resources. Tag Value length can't exceed 256 characters
        full_dep_mod = dep_mod[:256] if len(dep_mod) > 256 else dep_mod
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=full_dep_mod)

        # Import EKS Cluster
        provider = eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(self, "Provider", eks_oidc_arn)
        handler_role = iam.Role.from_role_arn(self, "HandlerRole", eks_handler_role_arn)
        eks_cluster = eks.Cluster.from_cluster_attributes(
            self,
            "EKSCluster",
            cluster_name=eks_cluster_name,
            kubectl_role_arn=eks_admin_role_arn,
            open_id_connect_provider=provider,
            kubectl_lambda_role=handler_role,
            kubectl_layer=KubectlV29Layer(self, "Kubectlv29Layer"),
        )

        # Create namespace for Ray to use
        eks_namespace = eks.KubernetesManifest(
            self,
            "Namespace",
            cluster=eks_cluster,
            manifest=[
                {
                    "apiVersion": "v1",
                    "kind": "Namespace",
                    "metadata": {"name": self.namespace_name},
                }
            ],
            overwrite=True,  # Create if not exists
        )

        service_account = eks_cluster.add_service_account("service-account", name=module_name, namespace=namespace_name)
        self.service_account = service_account

        service_account_role: iam.Role = cast(iam.Role, service_account.role)
        if data_bucket_name:
            service_account_role.add_to_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:PutObject",
                        "s3:GetObject",
                        "s3:AbortMultipartUpload",
                        "s3:ListBucket",
                        "s3:GetObjectVersion",
                        "s3:ListMultipartUploadParts",
                    ],
                    resources=[
                        f"arn:{self.partition}:s3:::{data_bucket_name}/*",
                        f"arn:{self.partition}:s3:::{data_bucket_name}",
                    ],
                )
            )

        rbac_role = eks_cluster.add_manifest(
            "rbac-role",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "Role",
                "metadata": {
                    "name": "module-owner",
                    "namespace": namespace_name,
                },
                "rules": [{"apiGroups": ["*"], "resources": ["*"], "verbs": ["*"]}],
            },
        )
        rbac_role.node.add_dependency(eks_namespace)

        rbac_role_binding = eks_cluster.add_manifest(
            "rbac-role-binding",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": {"name": module_name, "namespace": namespace_name},
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "Role",
                    "name": "module-owner",
                },
                "subjects": [
                    {"kind": "User", "name": f"{module_name}"},
                    {
                        "kind": "ServiceAccount",
                        "name": module_name,
                        "namespace": namespace_name,
                    },
                ],
            },
        )
        rbac_role_binding.node.add_dependency(service_account)

        rbac_role = eks_cluster.add_manifest(
            "rbac-role-default",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "Role",
                "metadata": {"name": "default-access", "namespace": "default"},
                "rules": [
                    {
                        "apiGroups": ["*"],
                        "resources": ["*"],
                        "verbs": ["get", "list", "watch"],
                    }
                ],
            },
        )
        rbac_role.node.add_dependency(eks_namespace)

        rbac_role_binding = eks_cluster.add_manifest(
            "rbac-role-binding-default",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": {"name": "default-access", "namespace": "default"},
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "Role",
                    "name": "default-access",
                },
                "subjects": [
                    {"kind": "User", "name": f"{module_name}"},
                    {
                        "kind": "ServiceAccount",
                        "name": module_name,
                        "namespace": namespace_name,
                    },
                ],
            },
        )
        rbac_role_binding.node.add_dependency(service_account)

        rbac_cluster_role_binding = eks_cluster.add_manifest(
            "rbac-cluster-role-binding",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRoleBinding",
                "metadata": {"name": f"system-access-{module_name}"},
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "ClusterRole",
                    "name": "system-access",
                },
                "subjects": [
                    {"kind": "User", "name": f"{module_name}"},
                    {
                        "kind": "ServiceAccount",
                        "name": module_name,
                        "namespace": namespace_name,
                    },
                ],
            },
        )
        rbac_cluster_role_binding.node.add_dependency(service_account)
