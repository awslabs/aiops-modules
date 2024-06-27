# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Optional

import cdk_nag
from aws_cdk import Stack, Environment
from constructs import Construct

from personas import Personas as PersonasConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class Personas(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        bucket_name: Optional[str],
        env: Environment,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id)

        s3_bucket_prefix = bucket_name or f"{construct_id}-bucket"
        self.personas = PersonasConstruct(
            self,
            construct_id="PersonasConstruct",
            s3_bucket_prefix=s3_bucket_prefix,
            env=env,
        )
        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.personas,
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