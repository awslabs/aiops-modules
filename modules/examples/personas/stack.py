# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any

import cdk_nag
from aws_cdk import Stack
from constructs import Construct

from personas import Personas as PersonasConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class Personas(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        app_prefix: str,
        bucket_name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id)

        self.personas = PersonasConstruct(
            self,
            construct_id="PersonasConstruct",
            app_prefix=app_prefix,
            bucket_name=bucket_name,
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
