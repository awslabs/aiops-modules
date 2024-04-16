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

import json
import os

MODEL_BUCKET_ARN = os.environ["MODEL_BUCKET_ARN"]
MODEL_PACKAGE_GROUP_NAME = os.getenv("MODEL_PACKAGE_GROUP_NAME", "")

DEV_ACCOUNT_ID = os.environ["DEV_ACCOUNT_ID"]
DEV_REGION = os.environ["DEV_REGION"]
DEV_VPC_ID = os.environ["DEV_VPC_ID"]
DEV_SUBNET_IDS = json.loads(os.environ["DEV_SUBNET_IDS"])
DEV_SECURITY_GROUP_IDS = json.loads(os.environ["DEV_SECURITY_GROUP_IDS"])

PRE_PROD_ACCOUNT_ID = os.environ["PRE_PROD_ACCOUNT_ID"]
PRE_PROD_REGION = os.environ["PRE_PROD_REGION"]
PRE_PROD_VPC_ID = os.environ["PRE_PROD_VPC_ID"]
PRE_PROD_SUBNET_IDS = json.loads(os.environ["PRE_PROD_SUBNET_IDS"])
PRE_PROD_SECURITY_GROUP_IDS = json.loads(os.environ["PRE_PROD_SECURITY_GROUP_IDS"])

PROD_ACCOUNT_ID = os.environ["PROD_ACCOUNT_ID"]
PROD_REGION = os.environ["PROD_REGION"]
PROD_VPC_ID = os.environ["PROD_VPC_ID"]
PROD_SUBNET_IDS = json.loads(os.environ["PROD_SUBNET_IDS"])
PROD_SECURITY_GROUP_IDS = json.loads(os.environ["PROD_SECURITY_GROUP_IDS"])

PROJECT_NAME = os.getenv("PROJECT_NAME", "")
PROJECT_ID = os.getenv("PROJECT_ID", "")

ECR_REPO_ARN = os.getenv("ECR_REPO_ARN", None)
