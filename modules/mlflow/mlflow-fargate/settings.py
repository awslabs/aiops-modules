"""Defines the stack settings."""

from abc import ABC

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
    subnet_ids: list[str]
    ecr_repository_name: str
    artifacts_bucket_name: str

    ecs_cluster_name: str | None = Field(default=None)
    service_name: str | None = Field(default=None)
    task_cpu_units: int = Field(default=4 * 1024)
    task_memory_limit_mb: int = Field(default=8 * 1024)
    autoscale_max_capacity: int = Field(default=10)
    lb_access_logs_bucket_name: str | None = Field(default=None)
    lb_access_logs_bucket_prefix: str | None = Field(default=None)
    efs_removal_policy: str = Field(default="RETAIN")

    rds_hostname: str | None = Field(default=None)
    rds_port: int | None = Field(default=None)
    rds_security_group_id: str | None = Field(default=None)
    rds_credentials_secret_arn: str | None = Field(default=None)

    @computed_field
    @property
    def rds_settings(self) -> RDSSettings | None:
        rds_values = [self.rds_hostname, self.rds_port, self.rds_security_group_id, self.rds_credentials_secret_arn]

        if all(rds_values):
            return RDSSettings(
                hostname=self.rds_hostname,
                port=self.rds_port,
                security_group_id=self.rds_security_group_id,
                credentials_secret_arn=self.rds_credentials_secret_arn,
            )
        elif not any(rds_values):
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

    @computed_field
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
