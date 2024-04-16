"""Seedfarmer module to deploy a SageMaker Model Package Group."""
from typing import Any, List, Optional

import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as events_targets
import aws_cdk.aws_sagemaker as sagemaker
from aws_cdk import CfnOutput, RemovalPolicy, Stack, Tags
from aws_cdk import aws_iam as iam
from constructs import Construct


class SagemakerModelPackageGroupStack(Stack):
    """Create a Sagemaker Model Package Group."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        model_package_group_name: str,
        retain_on_delete: bool = True,
        target_event_bus_arn: Optional[str] = None,
        model_package_group_description: Optional[str] = None,
        target_account_ids: Optional[List[str]] = None,
        sagemaker_project_id: Optional[str] = None,
        sagemaker_project_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Deploy a Sagemaker Model Package.

        Parameters
        ----------
        scope
            Parent of this stack, usually an ``App`` or a ``Stage``, but could be any construct
        construct_id
            The construct ID of this stack
        model_package_group_name
            The Model Package Group name.
        retain_on_delete, optional
            Wether or not to retain resources on delete. Defaults True.
        target_event_bus_arn, optional
            The event bus arn in to send events model package group state change events to.
            It can be a bus located in another account. Defaults None.
        model_package_group_description, optional
            The model package group description. Defaults None.
        target_account_ids, optional
            The target account ids which shall have read-only access to the model package group. Defaults None.
        sagemaker_project_id, optional
            SageMaker project id, defaults None
        sagemaker_project_name, optional
            SageMaker project name, defaults None
        """
        super().__init__(scope, construct_id, **kwargs)
        self.target_event_bus_arn = target_event_bus_arn
        self.target_account_ids = target_account_ids
        self.model_package_group_name = model_package_group_name

        self.removal_policy = (
            RemovalPolicy.RETAIN if retain_on_delete else RemovalPolicy.DESTROY
        )

        self.model_package_group_description = model_package_group_description
        self.sagemaker_project_name = sagemaker_project_name
        self.sagemaker_project_id = sagemaker_project_id

        self.setup_resources()

        self.setup_outputs()

        self.setup_tags()

    def setup_resources(self) -> None:
        """Deploy resources."""

        self.model_package_group = self.setup_model_package_group()

        self.event_rule = self.setup_events()

    def setup_model_package_group(self) -> sagemaker.CfnModelPackageGroup:
        """Create a Model Package Group."""
        model_package_group_policy = self.get_model_package_group_resource_policy()

        model_package_group = sagemaker.CfnModelPackageGroup(
            self,
            "ModelPackageGroup",
            model_package_group_name=self.model_package_group_name,
            model_package_group_description=self.model_package_group_description,
            model_package_group_policy=model_package_group_policy,
        )

        model_package_group.apply_removal_policy(self.removal_policy)

        return model_package_group

    def get_model_package_group_resource_policy(self) -> Optional[dict]:
        """Get a resource policy to enable cross account access into Sagemaker Model Package Group.

        Returns
        -------
            A resource policy with cross-account read-only permissions.
        """
        if not self.target_account_ids:
            return None

        sagemaker_arn = f"arn:aws:sagemaker:{self.region}:{self.account}"
        target_accounts = [f"arn:aws:iam::{a}:root" for a in self.target_account_ids]

        model_package_group_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "ModelPackageGroupPermissionSet",
                    "Effect": "Allow",
                    "Principal": {"AWS": target_accounts},
                    "Action": ["sagemaker:DescribeModelPackageGroup"],
                    "Resource": f"{sagemaker_arn}:model-package-group/{self.model_package_group_name}",
                },
                {
                    "Sid": "ModelPackagePermissionSet",
                    "Effect": "Allow",
                    "Principal": {"AWS": target_accounts},
                    "Action": [
                        "sagemaker:DescribeModelPackage",
                        "sagemaker:ListModelPackages",
                        "sagemaker:CreateModel",
                    ],
                    "Resource": f"{sagemaker_arn}:model-package/{self.model_package_group_name}/*",
                },
            ],
        }

        return model_package_group_policy

    def setup_events(self) -> Optional[events.Rule]:
        """Setup an event rule

        The event rule will send SageMaker Model Package State Change events to another EventBus.

        Returns
        -------
            An event rule
        """
        if not self.target_event_bus_arn:
            return None

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
            description=f"Rule to send events when `{self.model_package_group_name}` state changes",
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

    def setup_tags(self) -> None:
        """Add tags to all resources."""
        Tags.of(self).add("sagemaker:deployment-stage", Stack.of(self).stack_name)

        if self.sagemaker_project_id:
            Tags.of(self).add("sagemaker:project-id", self.sagemaker_project_id)

        if self.sagemaker_project_name:
            Tags.of(self).add("sagemaker:project-name", self.sagemaker_project_name)

    def setup_outputs(self) -> None:
        """Setups outputs and metadata."""
        metadata = {
            "SagemakerModelPackageGroupArn": self.model_package_group.attr_model_package_group_arn,
            "SagemakerModelPackageGroupName": self.model_package_group_name,
        }

        if self.event_rule:
            metadata[
                "SagemakerModelPackageGroupEventRuleArn"
            ] = self.event_rule.rule_arn

        for key, value in metadata.items():
            CfnOutput(scope=self, id=key, value=value)

        CfnOutput(scope=self, id="metadata", value=self.to_json_string(metadata))
