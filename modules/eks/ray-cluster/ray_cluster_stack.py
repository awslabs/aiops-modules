# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, Optional, cast

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
        ray_version: str,
        ray_cluster_helm_chart_version: str,
        image_uri: str,
        enable_autoscaling: bool,
        autoscaler_idle_timeout_seconds: int,
        head_resources: Dict[str, Dict[str, str]],
        worker_replicas: int,
        worker_min_replicas: int,
        worker_max_replicas: int,
        worker_resources: Dict[str, Dict[str, str]],
        worker_tolerations: List[Dict[str, str]],
        worker_labels: Dict[str, str],
        pvc_name: Optional[str],
        dra_export_path: str,
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

        volumes = [
            {"name": "log-volume", "emptyDir": {}},
            {"name": "dshm", "emptyDir": {"medium": "Memory"}},
        ]
        volume_mounts = [
            {"mountPath": "/tmp/ray", "name": "log-volume"},
            {"mountPath": "/dev/shm", "name": "dshm"},
        ]
        if pvc_name:
            volumes.append({"name": "persistent-storage", "persistentVolumeClaim": {"claimName": pvc_name}})
            # subPath should never start with `/`
            volume_mounts.append(
                {"mountPath": dra_export_path, "name": "persistent-storage", "subPath": dra_export_path[1:]}
            )

        [image_repository, image_tag] = image_uri.split(":")
        eks_cluster.add_helm_chart(
            "RayCluster",
            chart="ray-cluster",
            repository="https://ray-project.github.io/kuberay-helm/",
            namespace=namespace_name,
            version=ray_cluster_helm_chart_version,
            wait=True,
            values={
                "image": {
                    "repository": image_repository,
                    "tag": image_tag,
                    "pullPolicy": "IfNotPresent",
                },
                "nameOverride": "kuberay",
                "fullnameOverride": "kuberay",
                "head": {
                    "rayVersion": ray_version,
                    # Set rayStartParams num-cpus to 0 to prevent the Ray scheduler from
                    # scheduling any Ray actors or tasks on the Ray head Pod.
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
                    "resources": head_resources,
                    "volumes": volumes,
                    "volumeMounts": volume_mounts,
                },
                "worker": {
                    "replicas": worker_replicas,
                    "minReplicas": worker_min_replicas,
                    "maxReplicas": worker_max_replicas,
                    "serviceAccountName": service_account_name,
                    "resources": worker_resources,
                    "tolerations": worker_tolerations,
                    "volumes": volumes,
                    "volumeMounts": volume_mounts,
                    "nodeSelector": worker_labels,
                },
            },
        )
