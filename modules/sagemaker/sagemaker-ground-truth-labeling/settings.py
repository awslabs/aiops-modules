"""Defines the stack settings."""

from abc import ABC
from typing import Any, Dict, List, Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_TASK_CONFIG = {
    "NumberOfHumanWorkersPerDataObject": 1,
    "TaskAvailabilityLifetimeInSeconds": 21600,
    "TaskTimeLimitInSeconds": 300,
}


class CdkBaseSettings(BaseSettings, ABC):
    """Defines common configuration for settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        protected_namespaces=(),
        extra="ignore",
        populate_by_name=True,
    )


class ModuleSettings(CdkBaseSettings):
    """Seedfarmer Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    job_name: str
    task_type: str
    labeling_workteam_arn: str
    labeling_instructions_template_s3_uri: str = Field(default="")
    labeling_categories_s3_uri: str
    labeling_task_title: str
    labeling_task_description: str
    labeling_task_keywords: List[str]
    verification_workteam_arn: str = Field(default="")
    verification_instructions_template_s3_uri: str = Field(default="")
    verification_categories_s3_uri: str = Field(default="")
    verification_task_title: str = Field(default="")
    verification_task_description: str = Field(default="")
    verification_task_keywords: List[str] = Field(default=[])

    sqs_queue_retention_period: int = Field(default=60 * 24 * 14)
    sqs_queue_visibility_timeout: int = Field(default=60 * 12)
    sqs_queue_max_receive_count: int = Field(default=3)
    sqs_dlq_retention_period: int = Field(default=60 * 24 * 14)
    sqs_dlq_visibility_timeout: int = Field(default=60 * 12)
    sqs_dlq_alarm_threshold: int = Field(default=1)
    labeling_human_task_config: Dict[str, Any] = Field(default=DEFAULT_TASK_CONFIG)
    labeling_task_price: Dict[str, Dict[str, int]] = Field(default={})
    verification_human_task_config: Dict[str, Any] = Field(default=DEFAULT_TASK_CONFIG)
    verification_task_price: Dict[str, Dict[str, int]] = Field(default={})
    labeling_workflow_schedule: str = Field(default="cron(0 12 * * ? *)")
    permissions_boundary_name: Optional[str] = Field(default=None)


class SeedFarmerSettings(CdkBaseSettings):
    """Seedfarmer Settings.

    These parameters comes from seedfarmer by default.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_")

    project_name: str = Field(default="")
    deployment_name: str = Field(default="")
    module_name: str = Field(default="")

    @computed_field  # type: ignore
    @property
    def app_prefix(self) -> str:
        """Application prefix."""
        prefix = "-".join([self.project_name, self.deployment_name, self.module_name])
        return prefix


class CDKSettings(CdkBaseSettings):
    """CDK Default Settings.

    These parameters come from AWS CDK by default.
    """

    model_config = SettingsConfigDict(env_prefix="CDK_DEFAULT_")

    account: str
    region: str


class ApplicationSettings(CdkBaseSettings):
    """Application settings."""

    seedfarmer_settings: SeedFarmerSettings = Field(default_factory=SeedFarmerSettings)
    module_settings: ModuleSettings = Field(default_factory=ModuleSettings)
    cdk_settings: CDKSettings = Field(default_factory=CDKSettings)
