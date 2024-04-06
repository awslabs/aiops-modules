# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import aws_cdk as cdk
from config.constants import (
    DEPLOYMENT_ACCOUNT,
    DEPLOYMENT_REGION,
    PREPROD_ACCOUNT,
    PREPROD_REGION,
    PROD_ACCOUNT,
    PROD_REGION,
    DEV_VPC_ID,
    DEV_SUBNET_IDS,
    PRE_PROD_VPC_ID,
    PRE_PROD_SUBNET_IDS,
    PROD_VPC_ID,
    PROD_SUBNET_IDS
)
from deploy_endpoint.deploy_endpoint_stack import DeployEndpointStack

app = cdk.App()

dev_env = cdk.Environment(account=DEPLOYMENT_ACCOUNT, region=DEPLOYMENT_REGION)
preprod_env = cdk.Environment(account=PREPROD_ACCOUNT, region=PREPROD_REGION)
prod_env = cdk.Environment(account=PROD_ACCOUNT, region=PROD_REGION)

# DeployEndpointStack(app, "dev", env=dev_env)
# DeployEndpointStack(app, "preprod", env=preprod_env)
# DeployEndpointStack(app, "prod", env=prod_env)
DeployEndpointStack(app, "dev", vpc_id=DEV_VPC_ID, subnet_ids=DEV_SUBNET_IDS, env=dev_env)
DeployEndpointStack(app, "preprod", vpc_id=PRE_PROD_VPC_ID, subnet_ids=PRE_PROD_SUBNET_IDS, env=preprod_env)
DeployEndpointStack(app, "prod", vpc_id=PROD_VPC_ID, subnet_ids=PROD_SUBNET_IDS, env=prod_env)


app.synth()
