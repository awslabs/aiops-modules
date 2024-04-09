# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk as cdk
from config.constants import (
    DEV_ACCOUNT_ID,
    DEV_REGION,
    DEV_SECURITY_GROUP_IDS,
    DEV_SUBNET_IDS,
    DEV_VPC_ID,
    PRE_PROD_ACCOUNT_ID,
    PRE_PROD_REGION,
    PRE_PROD_SECURITY_GROUP_IDS,
    PRE_PROD_SUBNET_IDS,
    PRE_PROD_VPC_ID,
    PROD_ACCOUNT_ID,
    PROD_REGION,
    PROD_SECURITY_GROUP_IDS,
    PROD_SUBNET_IDS,
    PROD_VPC_ID,
)
from deploy_endpoint.deploy_endpoint_stack import DeployEndpointStack

app = cdk.App()

dev_env = cdk.Environment(account=DEV_ACCOUNT_ID, region=DEV_REGION)
preprod_env = cdk.Environment(account=PRE_PROD_ACCOUNT_ID, region=PRE_PROD_REGION)
prod_env = cdk.Environment(account=PROD_ACCOUNT_ID, region=PROD_REGION)

DeployEndpointStack(
    app, "dev", vpc_id=DEV_VPC_ID, subnet_ids=DEV_SUBNET_IDS, security_group_ids=DEV_SECURITY_GROUP_IDS, env=dev_env
)
DeployEndpointStack(
    app,
    "preprod",
    vpc_id=PRE_PROD_VPC_ID,
    subnet_ids=PRE_PROD_SUBNET_IDS,
    security_group_ids=PRE_PROD_SECURITY_GROUP_IDS,
    env=preprod_env,
)
DeployEndpointStack(
    app,
    "prod",
    vpc_id=PROD_VPC_ID,
    subnet_ids=PROD_SUBNET_IDS,
    security_group_ids=PROD_SECURITY_GROUP_IDS,
    env=prod_env,
)


app.synth()
