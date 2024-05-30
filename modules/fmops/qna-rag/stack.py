# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Optional

import cdk_nag
from aws_cdk import Stack
from aws_cdk import (
    aws_cognito as cognito,
)
from aws_cdk import aws_ec2 as ec2
from aws_cdk import (
    aws_opensearchservice as os,
)
from aws_cdk import aws_s3 as s3
from cdklabs.generative_ai_cdk_constructs import QaAppsyncOpensearch, RagAppsyncStepfnOpensearch
from constructs import Construct


class RAGResources(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc_id: str,
        cognito_pool_id: str,
        os_domain_endpoint: str,
        os_domain_port: int,
        os_security_group_id: str,
        os_index_name: str,
        input_asset_bucket_name: Optional[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            description=" This stack creates resources for the LLM - QA RAG ",
            **kwargs,
        )

        # get an existing OpenSearch provisioned cluster
        os_domain = os.Domain.from_domain_endpoint(
            self,
            "osdomain",
            domain_endpoint="https://" + os_domain_endpoint,
        )
        self.os_domain = os_domain

        # get vpc from vpc id
        vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        # get an existing userpool
        cognito_pool_id = cognito_pool_id
        user_pool_loaded = cognito.UserPool.from_user_pool_id(
            self,
            "myuserpool",
            user_pool_id=cognito_pool_id,
        )

        if input_asset_bucket_name:
            input_asset_bucket = s3.Bucket.from_bucket_name(self, "input-assets-bucket", input_asset_bucket_name)
        else:
            input_asset_bucket = None

        # 1. Create Ingestion pipeline
        rag_ingest_resource = RagAppsyncStepfnOpensearch(
            self,
            "RagAppsyncStepfnOpensearch",
            existing_vpc=vpc,
            existing_opensearch_domain=os_domain,
            open_search_index_name=os_index_name,
            cognito_user_pool=user_pool_loaded,
            existing_input_assets_bucket_obj=input_asset_bucket,
        )

        self.security_group_id = rag_ingest_resource.security_group.security_group_id

        self.rag_ingest_resource = rag_ingest_resource

        # 2. create question and answer pipeline
        rag_qa_source = QaAppsyncOpensearch(
            self,
            "QaAppsyncOpensearch",
            existing_vpc=vpc,
            existing_opensearch_domain=os_domain,
            open_search_index_name=os_index_name,
            cognito_user_pool=user_pool_loaded,
            existing_input_assets_bucket_obj=rag_ingest_resource.s3_processed_assets_bucket,
            existing_security_group=rag_ingest_resource.security_group,
        )

        security_group = rag_qa_source.security_group

        os_security_group = ec2.SecurityGroup.from_security_group_id(self, "OSSecurityGroup", os_security_group_id)
        os_security_group.add_ingress_rule(
            peer=security_group,
            connection=ec2.Port.tcp(os_domain_port),
            description="Allow inbound HTTPS to open search from embeddings lambda and question answering lambda",
        )

        self.rag_resource = rag_qa_source

        # 3. add cdk nag suppressions
        cdk_nag.NagSuppressions.add_stack_suppressions(
            self,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Created by the QaAppsyncOpensearch and RagAppsyncStepfnOpensearch constructs",
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSAppSyncPushToCloudWatchLogs",
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
                    ],
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Created by the QaAppsyncOpensearch and RagAppsyncStepfnOpensearch constructs",
                ),
            ],
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            rag_ingest_resource,
            apply_to_children=True,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-S10",
                    reason="We don't have control over the S3 bucket defined by RagAppsyncStepfnOpensearch",
                ),
            ],
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            rag_qa_source,
            apply_to_children=True,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason="We don't have control over the S3 bucket defined by QaAppsyncOpensearch",
                ),
            ],
        )
