#!/usr/bin/env python3

import aws_cdk as cdk
import config.constants as constants
from deploy_app.pipeline_stack import PipelineStack

app = cdk.App()

# All deployment regions must match - cross-region endpoint deployment is not supported
# because model packages contain region-specific container image URIs
regions = {
    "dev": constants.DEV_REGION,
    "pre-prod": constants.PRE_PROD_REGION,
    "prod": constants.PROD_REGION,
}
mismatched = {k: v for k, v in regions.items() if v != constants.DEV_REGION}
if mismatched:
    raise ValueError(f"All deployment regions must match dev region ({constants.DEV_REGION}). Mismatched: {mismatched}")

PipelineStack(
    app,
    f"{constants.PROJECT_NAME}-pipeline",
    env=cdk.Environment(account=constants.DEV_ACCOUNT_ID, region=constants.DEV_REGION),
)

app.synth()
