"""Defines the stack settings."""

from abc import ABC
from typing import List, Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from stack import RDSSettings


class CdkBaseSettings(BaseSettings, ABC):
    """Defines common configuration for settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_nested_delimiter="__",
        protected_namespaces=(),
        extra="ignore",
        populate_by_name=True,
    )


class SeedFarmerParameters(CdkBaseSettings):
    """Seedfarmer Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    vpc_id: str
    subnet_ids: List[str]
    ecr_repository_name: str
    artifacts_bucket_name: str

    ecs_cluster_name: Optional[str] = Field(default=None)
    service_name: Optional[str] = Field(default=None)
    task_cpu_units: int = Field(default=4 * 1024)
    task_memory_limit_mb: int = Field(default=8 * 1024)
    autoscale_max_capacity: int = Field(default=10)
    lb_access_logs_bucket_name: Optional[str] = Field(default=None)
    lb_access_logs_bucket_prefix: Optional[str] = Field(default=None)
    efs_removal_policy: str = Field(default="RETAIN")

    rds_hostname: Optional[str] = Field(default=None)
    rds_port: Optional[int] = Field(default=None)
    rds_security_group_id: Optional[str] = Field(default=None)
    rds_credentials_secret_arn: Optional[str] = Field(default=None)

    @computed_field  # type: ignore[misc]
    @property
    def rds_settings(self) -> Optional[RDSSettings]:
        if self.rds_hostname and self.rds_port and self.rds_security_group_id and self.rds_credentials_secret_arn:
            return RDSSettings(
                hostname=self.rds_hostname,
                port=self.rds_port,
                security_group_id=self.rds_security_group_id,
                credentials_secret_arn=self.rds_credentials_secret_arn,
            )
        elif not (self.rds_hostname or self.rds_port or self.rds_security_group_id or self.rds_credentials_secret_arn):
            return None
        else:
            raise ValueError(
                "Invalid combination of input parameters rds-hostname, rds-port, rds-security-group-id, "
                "and rds-credentials-secret-arn. "
                "They must either all be specified or none of them."
            )


class SeedFarmerSettings(CdkBaseSettings):
    """Seedfarmer Settings.

    These parameters comes from seedfarmer by default.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_")

    project_name: str = Field(default="")
    deployment_name: str = Field(default="")
    module_name: str = Field(default="")

    @computed_field  # type: ignore[misc]
    @property
    def app_prefix(self) -> str:
        """Application prefix."""
        prefix = "-".join([self.project_name, self.deployment_name, self.module_name])
        return prefix


class CdkDefaultSettings(CdkBaseSettings):
    """CDK Default Settings.

    These parameters comes from AWS CDK by default.
    """

    model_config = SettingsConfigDict(env_prefix="CDK_DEFAULT_")

    account: str
    region: str


class ApplicationSettings(CdkBaseSettings):
    """Application settings."""

    settings: SeedFarmerSettings = Field(default_factory=SeedFarmerSettings)
    parameters: SeedFarmerParameters = Field(default_factory=SeedFarmerParameters)
    default: CdkDefaultSettings = Field(default_factory=CdkDefaultSettings)
