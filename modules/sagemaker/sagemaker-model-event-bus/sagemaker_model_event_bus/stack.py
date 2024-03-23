"""Seedfarmer module to deploy an EventBridge Bus for SageMaker Model Package events."""
from typing import Any, Dict, List, Optional

import aws_cdk.aws_events as events
from aws_cdk import CfnOutput, Stack, Tags
from aws_cdk import aws_iam as iam
from constructs import Construct


class SagemakerModelEventBusStack(Stack):
    """Create an EventBridge Bus."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        event_bus_name: str,
        source_accounts: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        """Deploy an EventBridge Bus.

        Parameters
        ----------
        scope
            Parent of this stack, usually an ``App`` or a ``Stage``, but could be any construct
        construct_id
            The construct ID of this stack
        event_bus_name
            The EventBridge Bus name.
        source_accounts, optional
            A list of account ids to grant cross account put events permission. Defaults None.
        tags, optional
            Extra tags to apply to the EventBridge bus, by default None
        """
        super().__init__(scope, construct_id, **kwargs)
        self.event_bus_name = event_bus_name
        self.source_accounts = source_accounts
        self.additional_tags = tags

        self.setup_resources()

        self.setup_outputs()

        self.setup_tags()

    def setup_resources(self) -> None:
        """Deploy resources."""

        self.event_bus = self.create_event_bus()

    def create_event_bus(self) -> events.EventBus:
        """Create an Amazon EventBridge bus."""
        event_bus = events.EventBus(
            scope=self,
            id="EventBus",
            event_bus_name=self.event_bus_name,
        )

        if not self.source_accounts:
            return event_bus

        principals = [iam.AccountPrincipal(i) for i in self.source_accounts]

        event_bus.add_to_resource_policy(
            iam.PolicyStatement(
                sid="GrantCrossAccountPermissionsToPutEvents",
                actions=["events:PutEvents"],
                effect=iam.Effect.ALLOW,
                resources=[event_bus.event_bus_arn],
                principals=principals,
            )
        )

        return event_bus

    def setup_tags(self) -> None:
        """Add tags to all resources."""
        Tags.of(self).add("sagemaker:deployment-stage", Stack.of(self).stack_name)

        for k, v in (self.additional_tags or {}).items():
            Tags.of(self).add(k, v)

    def setup_outputs(self) -> None:
        """Setups outputs and metadata."""
        metadata = {
            "EventBusArn": self.event_bus.event_bus_arn,
            "EventBusName": self.event_bus.event_bus_name,
        }

        for key, value in metadata.items():
            CfnOutput(
                scope=self,
                id=key,
                value=value,
            )

        CfnOutput(
            scope=self,
            id="metadata",
            value=self.to_json_string(metadata),
        )
