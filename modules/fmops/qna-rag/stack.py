# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import RagAppsyncStepfnOpensearch
from cdklabs.generative_ai_cdk_constructs import QaAppsyncOpensearch
from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import (
    aws_opensearchservice as os,
    aws_cognito as cognito,
)


class RAGResources(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc_id: str,
        cognito_pool_id: str,
        os_domain_endpoint: str,
        os_security_group_id: str,
        os_index_name: str,
        **kwargs,
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
        # 1. Create Ingestion pipeline
        rag_ingest_resource = RagAppsyncStepfnOpensearch(
            self,
            "RagAppsyncStepfnOpensearch",
            existing_vpc=vpc,
            existing_opensearch_domain=os_domain,
            open_search_index_name=os_index_name,
            cognito_user_pool=user_pool_loaded,
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

        os_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "OSSecurityGroup", os_security_group_id
        )
        os_security_group.add_ingress_rule(
            peer=security_group,
            connection=ec2.Port.tcp(443),
            description="Allow inbound HTTPS to open search from embeddings lambda and question answering lambda",
        )

        self.rag_resource = rag_qa_source
