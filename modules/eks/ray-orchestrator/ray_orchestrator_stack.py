# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, cast

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
        eks_cluster_endpoint: str,
        eks_openid_connect_provider_arn: str,
        eks_cert_auth_data: str,
        namespace_name: str,
        service_account_name: str,
        service_account_role_arn: str,
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
            kubectl_layer=KubectlV29Layer(self, "Kubectlv29Layer"),
        )

        with open(os.path.join(project_dir, "scripts/training-6B.py"), "r") as f:
            ray_job_file = f.read()

        cluster.add_manifest(
            "RayJobConfigMap",
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": "rayjob",
                    "namespace": namespace_name,
                },
                "data": {"job.py": ray_job_file},
            },
        )

        service_account_role = iam.Role.from_role_arn(self, "ServiceAccountRole", service_account_role_arn)

        body = {
            "apiVerson": "batch/v1",
            "kind": "Job",
            "metadata": {
                "namespace": namespace_name,
                "name.$": "States.Format('job-{}', $$.Execution.Name)",
            },
            "spec": {
                "backoffLimit": 1,
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "serviceAccountName": service_account_name,
                        "containers": [
                            {
                                "name.$": "States.Format('job-{}', $$.Execution.Name)",
                                "image": "python:3.9.19",
                                "command": [
                                    "sh",
                                    "-c",
                                    (
                                        'pip install ray"[default,client]"==2.30.0 && cd /home/ray/sample/ && '
                                        'ray job submit --address ray://kuberay-head-svc:10001 '
                                        '--working-dir="." -- python job.py'
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
                                    "items": [{"key": "job.py", "path": "job.py"}]
                                },
                            }
                        ],
                    },
                },
            },
        }

        ek_run_job_state = sfn.CustomState(
            self,
            "EksRunJobState",
            state_json={
                "Type": "Task",
                "Resource": "arn:aws:states:::eks:runJob.sync",
                "Parameters": {
                    "ClusterName": eks_cluster_name,
                    "Namespace": namespace_name,
                    "CertificateAuthority": eks_cert_auth_data,
                    "Endpoint": eks_cluster_endpoint,
                    "LogOptions": {"RetrieveLogs": True},
                    "Job": body,
                },
            },
        )

        self.log_group = logs.LogGroup(self, "JobLogGroup")

        self.sm = sfn.StateMachine(  # noqa: F841
            self,
            "EKSRunJob",
            definition_body=sfn.DefinitionBody.from_chainable(sfn.Chain.start(ek_run_job_state)),
            timeout=Duration.minutes(15),
            logs=sfn.LogOptions(destination=self.log_group, level=sfn.LogLevel.ALL),
            role=service_account_role,
        )
