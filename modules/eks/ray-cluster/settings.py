"""Defines the stack settings."""

from abc import ABC
from typing import Dict, Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_POD_RESOURCES = {
    "limits": {
        "cpu": "1",
        "memory": "8G",
    },
    "requests": {
        "cpu": "1",
        "memory": "8G",
    },
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


class SeedFarmerParameters(CdkBaseSettings):
    """Seedfarmer Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    eks_cluster_name: str
    namespace: str
    eks_cluster_admin_role_arn: str
    eks_oidc_arn: str
    service_account_name: str
    pvc_name: str
    ray_version: str = Field(default="2.30.0")
    ray_cluster_helm_chart_version: str = Field(default="1.1.1")
    image_uri: str = Field(default="rayproject/ray-ml:2.30.0")
    enable_autoscaling: bool = Field(default=True)
    autoscaler_idle_timeout_seconds: int = Field(default=60)
    head_resources: Dict[str, Dict[str, str]] = Field(default=DEFAULT_POD_RESOURCES)
    worker_replicas: int = Field(default=1)
    worker_min_replicas: int = Field(default=1)
    worker_max_replicas: int = Field(default=10)
    worker_resources: Dict[str, Dict[str, str]] = Field(default=DEFAULT_POD_RESOURCES)
    tags: Optional[Dict[str, str]] = Field(default=None)


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
