# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, cast

from aws_cdk import Duration, Stack, Tags
from aws_cdk import aws_eks as eks
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_logs as logs
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class RayOnEKS(Stack):
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
        eks_cluster_endpoint: str,
        eks_cert_auth_data: str,
        namespace_name: str,
        service_account_role,
        ray_image_uri: str,
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
        cluster = eks.Cluster.from_cluster_attributes(
            self,
            "EKSCluster",
            cluster_name=eks_cluster_name,
            open_id_connect_provider=provider,
            kubectl_role_arn=eks_admin_role_arn,
        )

        cluster.add_helm_chart(
            "RayOperator",
            chart="kuberay-operator",
            release="kuberay-operator",
            repository="https://ray-project.github.io/kuberay-helm/",
            namespace=namespace_name,
            version="1.0.0",
            wait=True,
        )

        cluster.add_helm_chart(
            "RayCluster",
            chart="ray-cluster",
            release="ray-cluster",
            repository="https://ray-project.github.io/kuberay-helm/",
            namespace=namespace_name,
            version="1.0.0",
            wait=True,
            values={
                "image": {
                    "repository": "rayproject/ray-ml",
                    "tag": "2.20.0",
                    "pullPolicy": "IfNotPresent",
                },
                "head": {
                    "resources": {
                        "limits": {
                            "cpu": "4",
                            "memory": "24G",
                        },
                        "requests": {
                            "cpu": "4",
                            "memory": "12G",
                        },
                    },
                    "tolerations": [
                        {
                            "key": namespace_name,
                            "effect": "NoSchedule",
                            "operator": "Exists",
                        }
                    ],
                    "containerEnv": [
                        {
                            "name": "RAY_LOG_TO_STDERR",
                            "value": "1",
                        },
                    ],
                },
                "worker": {
                    "resources": {
                        "limits": {
                            "cpu": "8",
                            "memory": "24G",
                        },
                        "requests": {
                            "cpu": "4",
                            "memory": "12G",
                        },
                    },
                    "tolerations": [
                        {
                            "key": namespace_name,
                            "effect": "NoSchedule",
                            "operator": "Exists",
                        }
                    ],
                    "replicas": "0",
                    "minReplicas": "0",
                    "maxReplicas": "30",
                    "containerEnv": [
                        {
                            "name": "RAY_LOG_TO_STDERR",
                            "value": "1",
                        },
                    ],
                },
            },
        )

        sfn_body = {
            "apiVerson": "batch/v1",
            "kind": "Job",
            "metadata": {
                "namespace": namespace_name,
                "name.$": "States.Format('pytorch-training-{}', $$.Execution.Name)",
            },
            "spec": {
                "backoffLimit": 1,
                "template": {
                    "spec": {
                        "restartPolicy": "OnFailure",
                        "serviceAccountName": module_name,
                        "containers": [
                            {
                                "name": "ray-ml-benchmark-pytorch",
                                "image": ray_image_uri,
                                "imagePullPolicy": "Always",
                                "env": [
                                    {
                                        "name": "TRAINING_JOB_ID",
                                        "value.$": "States.Format('ray-pytorch-{}', $$.Execution.Name)",
                                    }
                                ],
                                # "resources": {"limits": {"nvidia.com/gpu": 1}},
                            }
                        ],
                        # "nodeSelector": {"usage": "gpu"}
                    },
                },
            },
        }

        self.log_group = logs.LogGroup(self, "EKSJobLogGroup")

        sm = sfn.StateMachine(
            self,
            "EKSJobStepFunction",
            definition_body=sfn.DefinitionBody.from_chainable(
                sfn.Chain.start(
                    sfn.CustomState(
                        self,
                        "EksJob",
                        state_json={
                            "Type": "Task",
                            "Resource": "arn:aws:states:::eks:runJob.sync",
                            "Parameters": {
                                "ClusterName": eks_cluster_name,
                                "Namespace": namespace_name,
                                "CertificateAuthority": eks_cert_auth_data,
                                "Endpoint": eks_cluster_endpoint,
                                "LogOptions": {"RetrieveLogs": True},
                                "Job": sfn_body,
                            },
                        },
                    )
                )
            ),
            timeout=Duration.minutes(30),
            logs=sfn.LogOptions(destination=self.log_group, level=sfn.LogLevel.ALL),
            role=service_account_role,
        )
