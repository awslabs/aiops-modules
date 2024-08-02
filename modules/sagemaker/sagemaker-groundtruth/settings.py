"""Defines the stack settings."""

from abc import ABC
from typing import Dict, Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    repo_name: str = Field("aiops-to-greengrass-cs")
    branch_name: str = Field("main")
    pipeline_assets_prefix: str = Field("pipeline/labeling")
    use_private_workteam_for_labeling: bool = Field(False)
    use_private_workteam_for_verification: bool = Field(False)
    max_labels_per_labeling_job: int = Field(200)
    labeling_job_private_workteam_arn: Optional[str] = Field(
        "arn:aws:sagemaker:eu-west-1:0000000000000:workteam/private-crowd/GT1"
    )
    verification_job_private_workteam_arn: Optional[str] = Field(
        "arn:aws:sagemaker:eu-west-1:0000000000000:workteam/private-crowd/GT1"
    )
    labeling_pipeline_schedule: str = Field("cron(0 12 1 * ? *)")
    feature_group_name: str = Field("tag-quality-inspection")
    model_package_group_name: str = Field("TagQualityInspectionPackageGroup")
    model_package_group_description: str = Field(
        "Contains models for quality inspection of metal tags"
    )
    repoType: str = Field("CODECOMMIT")
    repoName: str = Field("aiops-for-quality-inspection")
    githubConnectionArn: Optional[str] = Field(None)
    githubRepoOwner: str = Field("aiops")
    branchName: str = Field("main")

    tags: Optional[Dict[str, str]] = Field(default=None)


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
    parameters: SeedFarmerParameters = Field(default_factory=SeedFarmerParameters)  # type: ignore[arg-type]
    default: CdkDefaultSettings = Field(default_factory=CdkDefaultSettings)  # type: ignore[arg-type]
