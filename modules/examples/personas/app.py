# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk

from settings import ApplicationSettings
from stack import Personas

app = aws_cdk.App()
# Load application settings from env vars.
app_settings = ApplicationSettings()


stack = Personas(
    scope=app,
    construct_id=app_settings.settings.app_prefix,
    bucket_name=app_settings.parameters.bucket_name,
    env=aws_cdk.Environment(
        account=app_settings.default.account,
        region=app_settings.default.region,
    ),
)

aws_cdk.CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "MLEngineerRoleArn": stack.personas.ml_engineer_role.role_arn,
            "DataEngineerRoleArn": stack.personas.data_engineer_role.role_arn,
            "ITLeadRoleArn": stack.personas.it_lead_role.role_arn,
            "BusinessAnalystRoleArn": stack.personas.business_analyst_role.role_arn,
            "MLOpsEngineerRoleArn": stack.personas.mlops_engineer_role.role_arn,
            "ITAuditorRoleArn": stack.personas.it_auditor_role.role_arn,
            "ModelRiskManagerRoleArn": stack.personas.model_risk_manager_role.role_arn,
        }
    ),
)

app.synth()
