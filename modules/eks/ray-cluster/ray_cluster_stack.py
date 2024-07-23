# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, cast

from aws_cdk import Stack, Tags
from aws_cdk import aws_eks as eks
from aws_cdk.lambda_layer_kubectl_v29 import KubectlV29Layer
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class RayCluster(Stack):
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
        eks_openid_connect_provider_arn: str,
        namespace_name: str,
        service_account_name: str,
        enable_autoscaling: bool,
        autoscaler_idle_timeout_seconds: int,
        worker_replicas: int,
        worker_min_replicas: int,
        worker_max_replicas: int,
        **kwargs: Any,
    ) -> None:
        self.project_name = project_name
        self.deployment_name = deployment_name
        self.module_name = module_name

        super().__init__(
            scope,
            id,
            **kwargs,
        )

        dep_mod = f"{project_name}-{deployment_name}-{module_name}"
        # used to tag AWS resources. Tag Value length can't exceed 256 characters
        full_dep_mod = dep_mod[:256] if len(dep_mod) > 256 else dep_mod
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=full_dep_mod)

        provider = eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self, "OIDCProvider", eks_openid_connect_provider_arn
        )

        eks_cluster = eks.Cluster.from_cluster_attributes(
            self,
            "EKSCluster",
            cluster_name=eks_cluster_name,
            open_id_connect_provider=provider,
            kubectl_role_arn=eks_admin_role_arn,
            kubectl_layer=KubectlV29Layer(self, "Kubectlv29Layer"),
        )

        eks_cluster.add_helm_chart(
            "RayCluster",
            chart="ray-cluster",
            repository="https://ray-project.github.io/kuberay-helm/",
            namespace=namespace_name,
            version="1.1.1",
            wait=True,
            values={
                "image": {
                    "repository": "rayproject/ray-ml",
                    "tag": "2.23.0",
                    "pullPolicy": "IfNotPresent",
                },
                "nameOverride": "kuberay",
                "fullnameOverride": "kuberay",
                "head": {
                    "rayVersion": "2.23.0",
                    "rayStartParams": {"num-cpus": "0"},
                    "serviceAccountName": service_account_name,
                    "enableInTreeAutoscaling": enable_autoscaling,
                    "autoscalerOptions": {
                        "upscalingMode": "Default",
                        "idleTimeoutSeconds": autoscaler_idle_timeout_seconds,
                        # The default Autoscaler resource limits and requests
                        # should be sufficient for production use-cases.
                        "resources": {
                            "limits": {
                                "cpu": "500m",
                                "memory": "512Mi",
                            },
                            "requests": {
                                "cpu": "500m",
                                "memory": "512Mi",
                            },
                        },
                    },
                    "resources": {"limits": {"cpu": "1", "memory": "8G"}, "requests": {"cpu": "1", "memory": "8G"}},
                    "volumes": [{"name": "log-volume", "emptyDir": {}}],
                    "volumeMounts": [{"mountPath": "/tmp/ray", "name": "log-volume"}],
                },
                "worker": {
                    "replicas": worker_replicas,
                    "minReplicas": worker_min_replicas,
                    "maxReplicas": worker_max_replicas,
                    "serviceAccountName": service_account_name,
                    # TODO: make all this configurable obviously
                    "resources": {"limits": {"cpu": "4", "memory": "24G"}, "requests": {"cpu": "4", "memory": "24G"}},
                    "volumes": [{"name": "log-volume", "emptyDir": {}}],
                    "volumeMounts": [{"mountPath": "/tmp/ray", "name": "log-volume"}],
                },
                "service": {
                    "type": "ClusterIP",
                },
            },
        )

        """
        ray_service = eks_cluster.add_manifest(
            "RayService",
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": module_name,
                    "namespace": namespace_name,
                },
                "spec": {
                    "selector": {"ray.io/node-type": "head"},
                    "ports": [
                        {"port": 8265, "targetPort": 8265, "name": "dashboard"},
                        {"port": 10001, "targetPort": 10001, "name": "client"},
                        {"port": 6379, "targetPort": 6379, "name": "gcs"},
                        {"port": 8000, "targetPort": 8000, "name": "serve"},
                        {"port": 8080, "targetPort": 8080, "name": "metrics"},
                    ],
                },
            },
        )
        ray_service.node.add_dependency(ray_cluster)
        """
