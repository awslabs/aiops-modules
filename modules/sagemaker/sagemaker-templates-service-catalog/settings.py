"""Defines the stack settings."""

from abc import ABC
from typing import Dict, List, Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from common.code_repo_construct import RepositoryType


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

    portfolio_name: str = Field(default="MLOps SageMaker Project Templates")
    portfolio_owner: str = Field(default="administrator")
    portfolio_access_role_arn: str

    dev_vpc_id: str = Field(default="")
    dev_subnet_ids: List[str] = Field(default=[])
    dev_security_group_ids: List[str] = Field(default=[])

    pre_prod_account_id: str = Field(default="")
    pre_prod_region: str = Field(default="")
    pre_prod_vpc_id: str = Field(default="")
    pre_prod_subnet_ids: List[str] = Field(default=[])
    pre_prod_security_group_ids: List[str] = Field(default=[])

    prod_account_id: str = Field(default="")
    prod_region: str = Field(default="")
    prod_vpc_id: str = Field(default="")
    prod_subnet_ids: List[str] = Field(default=[])
    prod_security_group_ids: List[str] = Field(default=[])

    sagemaker_domain_id: str = Field(default="")
    sagemaker_domain_arn: str = Field(default="")

    repository_type: RepositoryType = Field(default=RepositoryType.GITHUB)
    access_token_secret_name: str = Field(default="github_token")
    aws_codeconnection_arn: str = Field(default="")
    repository_owner: str = Field(default="")

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


class CDKSettings(CdkBaseSettings):
    """CDK Default Settings.

    These parameters comes from AWS CDK by default.
    """

    model_config = SettingsConfigDict(env_prefix="CDK_DEFAULT_")

    account: str
    region: str


class ApplicationSettings(CdkBaseSettings):
    """Application settings."""

    seedfarmer_settings: SeedFarmerSettings = Field(default_factory=SeedFarmerSettings)
    module_settings: ModuleSettings = Field(default_factory=ModuleSettings)
    cdk_settings: CDKSettings = Field(default_factory=CDKSettings)
