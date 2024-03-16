"""Seedfarmer module to deploy a SageMaker Model Package."""

import logging
import pathlib
from typing import Any, Optional

import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as events_targets
from aws_cdk import CfnOutput, Stack, Tags
from aws_cdk import aws_iam as iam
from constructs import Construct

logging.basicConfig()
logger = logging.getLogger(pathlib.Path(__file__).name)


class SagemakerModelPackageEventStack(Stack):
    """Create a Sagemaker Model Package Event Rule."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        target_event_bus_name: str,
        target_account_id: str,
        model_package_group_name: str,
        sagemaker_project_id: Optional[str] = None,
        sagemaker_project_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Deploy a Sagemaker Model Package Event Rule.

        Parameters
        ----------
        scope
            Parent of this stack, usually an ``App`` or a ``Stage``, but could be any construct
        construct_id
            The construct ID of this stack
        target_event_bus_name
            The event bus name in the target account to send events to.
        target_account_id
            The target account id which shall receive events and must have access to model package group metadata.
        model_package_group_name
            SageMaker Package Group Name to setup event rules.
        sagemaker_project_id
            SageMaker project id, defaults None
        sagemaker_project_name
            SageMaker project name, defaults None
        """
        super().__init__(scope, construct_id, **kwargs)
        self.target_event_bus_arn = f"arn:aws:events:{self.region}:{target_account_id}:event-bus/{target_event_bus_name}"
        self.target_account_id = target_account_id
        self.model_package_group_name = model_package_group_name

        self.sagemaker_project_name = sagemaker_project_name
        self.sagemaker_project_id = sagemaker_project_id

        self.setup_resources()

        self.setup_outputs()

        self.setup_tags()

    def setup_resources(self) -> None:
        """Deploy resources."""

        self.role = self.setup_role()

        self.rule = self.setup_events()

    def setup_events(self) -> events.Rule:
        """Setup an event rule

        The event rule will send SageMaker Model Package State Change events to another EventBus.

        Returns
        -------
            An event rule
        """
        rule = events.Rule(
            self,
            "SageMakerModelPackageStateChangeRule",
            event_pattern=events.EventPattern(
                source=["aws.sagemaker"],
                detail_type=["SageMaker Model Package State Change"],
                detail={
                    "ModelPackageGroupName": [self.model_package_group_name],
                    "ModelApprovalStatus": ["Approved", "Rejected"],
                },
            ),
            description=f"Rule to send events when `{self.model_package_group_name}` SageMaker Model Package state changes",
        )

        target_role = iam.Role(
            self,
            "SageMakerModelPackageStateChangeRuleTargetRole",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
            path="/service-role/",
        )

        target_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "events:PutEvents",
                ],
                effect=iam.Effect.ALLOW,
                resources=[self.target_event_bus_arn],
            )
        )

        target = events_targets.EventBus(
            event_bus=events.EventBus.from_event_bus_arn(
                scope=self, id="TargetEventBus", event_bus_arn=self.target_event_bus_arn
            ),
            role=target_role,
        )

        rule.add_target(target)

        return rule

    def setup_role(self) -> iam.Role:
        """Setup an IAM Role to get model package group metadata.

        This IAM role allows a target account to get model package group metadata.

        Returns
        -------
            An IAM role
        """
        role = iam.Role(
            self,
            "Role",
            assumed_by=iam.AccountPrincipal(self.target_account_id),
            path="/service-role/",
        )

        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:DescribeModelPackageGroup",
                    "sagemaker:DescribeModelPackage",
                    "sagemaker:ListModelPackages",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:model-package-group/{self.model_package_group_name}",
                    f"arn:aws:sagemaker:{self.region}:{self.account}:model-package/*",
                ],
            )
        )

        return role

    def setup_tags(self) -> None:
        """Add tags to all resources."""
        Tags.of(self).add("sagemaker:deployment-stage", Stack.of(self).stack_name)

        if self.sagemaker_project_id:
            Tags.of(self).add("sagemaker:project-id", self.sagemaker_project_id)

        if self.sagemaker_project_name:
            Tags.of(self).add("sagemaker:project-name", self.sagemaker_project_name)

    def setup_outputs(self) -> None:
        """Setups outputs and metadata."""
        CfnOutput(scope=self, id="RoleArn", value=self.role.role_arn)
        CfnOutput(scope=self, id="RuleArn", value=self.rule.rule_arn)

        CfnOutput(
            scope=self,
            id="metadata",
            value=self.to_json_string(
                {"RoleArn": self.role.role_arn, "RuleArn": self.rule.rule_arn}
            ),
        )
