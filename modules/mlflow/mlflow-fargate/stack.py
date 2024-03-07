# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, List, Optional, TypedDict, cast

import aws_cdk as cdk
import cdk_nag
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_efs as efs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3
from constructs import Construct, IConstruct


class RDSSettings(TypedDict):
    hostname: str
    port: int
    credentials_secret_arn: str
    security_group_id: str


class MlflowFargateStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        app_prefix: str,
        vpc_id: str,
        subnet_ids: List[str],
        ecs_cluster_name: Optional[str],
        service_name: Optional[str],
        ecr_repo_name: str,
        task_cpu_units: int,
        task_memory_limit_mb: int,
        autoscale_max_capacity: int,
        artifacts_bucket_name: str,
        rds_settings: Optional[RDSSettings],
        lb_access_logs_bucket_name: Optional[str],
        lb_access_logs_bucket_prefix: Optional[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        cdk.Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=app_prefix[:64])

        task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonECS_FullAccess"),
            ],
        )

        # Grant artifacts bucket read-write permissions
        model_bucket = s3.Bucket.from_bucket_name(self, "ArtifactsBucket", bucket_name=artifacts_bucket_name)
        model_bucket.grant_read_write(task_role)

        vpc = ec2.Vpc.from_lookup(self, "Vpc", vpc_id=vpc_id)
        subnets = [ec2.Subnet.from_subnet_id(self, f"Subnet {subnet_id}", subnet_id) for subnet_id in subnet_ids]

        # Create ECS cluster
        cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name=ecs_cluster_name,
            vpc=vpc,
            container_insights=True,
        )
        self.cluster = cluster

        task_definition = ecs.FargateTaskDefinition(
            self,
            "MlflowTask",
            task_role=task_role,
            cpu=task_cpu_units,
            memory_limit_mib=task_memory_limit_mb,
        )

        container = self._add_container_to_task_definition(
            task_definition=task_definition,
            image=ecs.ContainerImage.from_ecr_repository(
                repository=ecr.Repository.from_repository_name(
                    self,
                    "ECRRepo",
                    repository_name=ecr_repo_name,
                ),
            ),
            logging=ecs.LogDriver.aws_logs(stream_prefix="mlflow"),
            model_bucket=model_bucket,
            rds_settings=rds_settings,
        )

        port_mapping = ecs.PortMapping(container_port=5000, host_port=5000, protocol=ecs.Protocol.TCP)
        container.add_port_mappings(port_mapping)

        # Add EFS
        fs = efs.FileSystem(
            self,
            "EfsFileSystem",
            vpc=vpc,
            encrypted=True,
            throughput_mode=efs.ThroughputMode.ELASTIC,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            file_system_policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=[
                            "elasticfilesystem:ClientMount",
                            "elasticfilesystem:ClientWrite",
                            "elasticfilesystem:ClientRootAccess",
                        ],
                        principals=[iam.AnyPrincipal()],
                        resources=["*"],
                        conditions={"Bool": {"elasticfilesystem:AccessedViaMountTarget": "true"}},
                    ),
                ]
            ),
        )
        self.fs = fs

        # Attach and mount volume
        task_definition.add_volume(
            name="efs-volume",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=fs.file_system_id,
                transit_encryption="ENABLED",
            ),
        )
        container.add_mount_points(
            ecs.MountPoint(
                container_path="./mlruns",
                source_volume="efs-volume",
                read_only=False,
            )
        )

        # Create ECS Service
        fargate_service = ecs_patterns.NetworkLoadBalancedFargateService(
            self,
            "MlflowLBService",
            service_name=service_name,
            cluster=cluster,
            task_definition=task_definition,
            task_subnets=ec2.SubnetSelection(subnets=subnets),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
        )
        self.fargate_service = fargate_service

        # Enable access logs
        if lb_access_logs_bucket_name:
            lb_access_logs_bucket = s3.Bucket.from_bucket_name(
                self, "LBAccessLogsBucket", bucket_name=lb_access_logs_bucket_name
            )
        else:
            lb_access_logs_bucket = s3.Bucket(
                self,
                "LBAccessLogsBucket",
                encryption=s3.BucketEncryption.S3_MANAGED,
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                enforce_ssl=True,
            )
        fargate_service.load_balancer.log_access_logs(bucket=lb_access_logs_bucket, prefix=lb_access_logs_bucket_prefix)
        self.lb_access_logs_bucket = lb_access_logs_bucket

        # Allow access to EFS from Fargate service
        fs.grant_root_access(fargate_service.task_definition.task_role.grant_principal)
        fs.connections.allow_default_port_from(fargate_service.service.connections)

        # Setup security group
        fargate_security_group = fargate_service.service.connections.security_groups[0]
        fargate_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(5000),
            description="Allow inbound from VPC for mlflow",
        )

        # Setup RDS security group if needed
        if rds_settings:
            rds_security_group = ec2.SecurityGroup.from_security_group_id(
                self, "RDS Security Group", rds_settings["security_group_id"]
            )
            rds_security_group.add_ingress_rule(
                peer=ec2.Peer.security_group_id(fargate_security_group.security_group_id),
                connection=ec2.Port.tcp(rds_settings["port"]),
                description="Allow inbound access to RDS for mlflow",
            )

        # Setup autoscaling policy
        scaling = fargate_service.service.auto_scale_task_count(max_capacity=autoscale_max_capacity)
        scaling.scale_on_cpu_utilization(
            id="AutoscalingPolicy",
            target_utilization_percent=70,
            scale_in_cooldown=cdk.Duration.seconds(60),
            scale_out_cooldown=cdk.Duration.seconds(60),
        )

        # Add CDK nag suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions(
            [task_role, task_definition.execution_role],
            apply_to_children=True,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Managed Policies are for src account roles only",
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Resource access restricted to resources",
                ),
            ],
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            task_definition,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-ECS2",
                    reason="Not passing secrets via env variables",
                ),
            ],
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            lb_access_logs_bucket,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason="Access logs not required for access logs bucket",
                ),
            ],
        )

    def _add_container_to_task_definition(
        self,
        task_definition: ecs.FargateTaskDefinition,
        image: ecs.EcrImage,
        logging: ecs.LogDriver,
        model_bucket: s3.IBucket,
        rds_settings: Optional[RDSSettings],
    ) -> ecs.ContainerDefinition:
        if rds_settings:
            secret = rds.DatabaseSecret.from_secret_complete_arn(self, "Secret", rds_settings["credentials_secret_arn"])

            return task_definition.add_container(
                "ContainerDef",
                image=image,
                environment={
                    "BUCKET": model_bucket.s3_url_for_object(),
                    "HOST": rds_settings["hostname"],
                    "PORT": str(rds_settings["port"]),
                    "DATABASE": secret.secret_value_from_json("dbname").to_string(),
                    "USERNAME": secret.secret_value_from_json("username").to_string(),
                },
                secrets={
                    "PASSWORD": ecs.Secret.from_secrets_manager(secret, "password"),
                },
                logging=logging,
            )

        return task_definition.add_container(
            "ContainerDef",
            image=image,
            environment={
                "BUCKET": model_bucket.s3_url_for_object(),
            },
            logging=logging,
        )
