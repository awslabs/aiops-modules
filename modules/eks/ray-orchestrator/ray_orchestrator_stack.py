# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, Optional, cast

from aws_cdk import Duration, Stack, Tags
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk.lambda_layer_kubectl_v29 import KubectlV29Layer
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)

project_dir = os.path.dirname(os.path.abspath(__file__))


class RayOrchestrator(Stack):
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
        eks_handler_role_arn: str,
        eks_cluster_endpoint: str,
        eks_openid_connect_provider_arn: str,
        eks_cert_auth_data: str,
        namespace_name: str,
        step_function_timeout: int,
        service_account_name: str,
        service_account_role_arn: str,
        pvc_name: Optional[str],
        dra_export_path: str,
        permissions_boundary_name: Optional[str] = None,
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

        provider = eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self, "OIDCProvider", eks_openid_connect_provider_arn
        )
        handler_role = iam.Role.from_role_arn(self, "HandlerRole", eks_handler_role_arn)

        cluster = eks.Cluster.from_cluster_attributes(
            self,
            "EKSCluster",
            cluster_name=eks_cluster_name,
            open_id_connect_provider=provider,
            kubectl_role_arn=eks_admin_role_arn,
            kubectl_layer=KubectlV29Layer(self, "Kubectlv29Layer"),
            kubectl_lambda_role=handler_role,
        )

        service_account_role = iam.Role.from_role_arn(self, "ServiceAccountRole", service_account_role_arn)

        with open(os.path.join(project_dir, "scripts/training-6B.py"), "r") as f:
            training_job_file = f.read()
        with open(os.path.join(project_dir, "scripts/inference-6B.py"), "r") as f:
            inference_job_file = f.read()

        cluster.add_manifest(
            "RayJobConfigMap",
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": "rayjob",
                    "namespace": namespace_name,
                },
                "data": {
                    "training-6B.py": training_job_file,
                    "inference-6B.py": inference_job_file,
                },
            },
        )

        training_body = {
            "apiVerson": "batch/v1",
            "kind": "Job",
            "metadata": {
                "namespace": namespace_name,
                "name.$": "States.Format('job-training-{}', $$.Execution.Name)",
            },
            "spec": {
                "backoffLimit": 1,
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "serviceAccountName": service_account_name,
                        "containers": [
                            {
                                "name.$": "States.Format('job-training-{}', $$.Execution.Name)",
                                "image": "python:3.9.19",
                                "command": [
                                    "sh",
                                    "-c",
                                    (
                                        'pip install ray"[default,client]"==2.30.0 && cd /home/ray/sample/ && '
                                        "ray job submit --address ray://kuberay-head-svc:10001 "
                                        '--working-dir="." -- python training-6B.py'
                                    ),
                                ],
                                "volumeMounts": [{"name": "code-sample", "mountPath": "/home/ray/sample"}],
                            }
                        ],
                        "volumes": [
                            {
                                "name": "code-sample",
                                "configMap": {
                                    "name": "rayjob",
                                    "items": [{"key": "training-6B.py", "path": "training-6B.py"}],
                                },
                            }
                        ],
                    },
                },
            },
        }

        volumes = [
            {
                "name": "code-sample",
                "configMap": {"name": "rayjob", "items": [{"key": "inference-6B.py", "path": "inference-6B.py"}]},
            }
        ]
        volume_mounts = [{"name": "code-sample", "mountPath": "/home/ray/sample"}]

        # Mount the PVC to inference container to read model artifacts
        if pvc_name:
            volumes.append({"name": "persistent-storage", "persistentVolumeClaim": {"claimName": pvc_name}})
            # subPath should never start with `/`
            volume_mounts.append(
                {"mountPath": dra_export_path, "name": "persistent-storage", "subPath": dra_export_path[1:]}
            )

        inference_body = {
            "apiVerson": "batch/v1",
            "kind": "Job",
            "metadata": {
                "namespace": namespace_name,
                "name.$": "States.Format('job-inference-{}', $$.Execution.Name)",
            },
            "spec": {
                "backoffLimit": 1,
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "serviceAccountName": service_account_name,
                        "containers": [
                            {
                                "name.$": "States.Format('job-inference-{}', $$.Execution.Name)",
                                "image": "rayproject/ray-ml:2.30.0",
                                "command": [
                                    "sh",
                                    "-c",
                                    ("cd /home/ray/sample/ && python inference-6B.py"),
                                ],
                                "volumeMounts": volume_mounts,
                            }
                        ],
                        "volumes": volumes,
                        "nodeSelector": {"usage": "gpu"},
                        "tolerations": [
                            {
                                "key": "nvidia.com/gpu",
                                "value": "true",
                                "effect": "NoSchedule",
                            }
                        ],
                    },
                },
            },
        }

        ek_run_training_job_state = sfn.CustomState(
            self,
            "StartTrainingJob",
            state_json={
                "Type": "Task",
                "Resource": "arn:aws:states:::eks:runJob.sync",
                "Parameters": {
                    "ClusterName": eks_cluster_name,
                    "Namespace": namespace_name,
                    "CertificateAuthority": eks_cert_auth_data,
                    "Endpoint": eks_cluster_endpoint,
                    "LogOptions": {"RetrieveLogs": False},
                    "Job": training_body,
                },
            },
        )

        ek_run_inference_job_state = sfn.CustomState(
            self,
            "StartInference",
            state_json={
                "Type": "Task",
                "Resource": "arn:aws:states:::eks:runJob.sync",
                "Parameters": {
                    "ClusterName": eks_cluster_name,
                    "Namespace": namespace_name,
                    "CertificateAuthority": eks_cert_auth_data,
                    "Endpoint": eks_cluster_endpoint,
                    "LogOptions": {"RetrieveLogs": True},
                    "Job": inference_body,
                },
            },
        )

        self.log_group = logs.LogGroup(self, "JobLogGroup")

        self.sm = sfn.StateMachine(  # noqa: F841
            self,
            "TrainingOnEks",
            definition_body=sfn.DefinitionBody.from_chainable(
                sfn.Chain.start(ek_run_training_job_state).next(ek_run_inference_job_state)
            ),
            timeout=Duration.minutes(int(step_function_timeout)),
            logs=sfn.LogOptions(destination=self.log_group, level=sfn.LogLevel.ALL),
            role=service_account_role,
        )
