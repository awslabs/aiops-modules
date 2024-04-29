# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from constructs import Construct
from cdklabs.generative_ai_cdk_constructs import QaAppsyncOpensearch
from aws_cdk import Stack
from aws_cdk import (
    aws_opensearchservice as os,
    aws_cognito as cognito,
)


class RAGResources(Stack):
    def __init__(self,
                 scope: Construct,
                 id: str,
                 cognito_pool_id: str ,
                 os_domain_endpoint: str,
                 **kwargs):
        super().__init__ \
            (scope,
             id,
             description=" This stack creates resources for the LLM - QA RAG ",
             **kwargs)

        print(os_domain_endpoint)
        # get an existing OpenSearch provisioned cluster
        os_domain = os.Domain.from_domain_endpoint(
            self,
            'osdomain',
            # domain_arn=open_search_domain_arn, #'arn:aws:es:us-east-1:098191324367:domain/osforqadomain',
            domain_endpoint= "https://" + os_domain_endpoint ,#'https://vpc-osforqadomain-du6zvbtupkxxsk3oouvjc5tkqy.us-east-1.es.amazonaws.com',
        )

        # get an existing userpool
        cognito_pool_id = cognito_pool_id
        user_pool_loaded = cognito.UserPool.from_user_pool_id(
            self,
            'myuserpool',
            user_pool_id=cognito_pool_id,
        )

        rag_source = QaAppsyncOpensearch(
            self,
            'QaAppsyncOpensearch',
            existing_opensearch_domain=os_domain,
            open_search_index_name='qa-appsync-index',
            cognito_user_pool=user_pool_loaded,
        )
