"""Defines the stack settings."""

from abc import ABC
from typing import Dict, List, Optional

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


class ModuleSettings(CdkBaseSettings):
    """SeedFarmer Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    endpoint_name: str

    security_group_id: Optional[str] = Field(default=None)
    subnet_ids: Optional[List[str]] = Field(default=None)
    # model_package_arn: str
    model_bucket_arn: str
    kms_key_id: Optional[str] = Field(default=None)

    sagemaker_project_id: Optional[str] = Field(default=None)
    sagemaker_project_name: Optional[str] = Field(default=None)

    enable_data_quality_monitor: bool = Field(default=False)
    enable_model_quality_monitor: bool = Field(default=False)
    enable_model_bias_monitor: bool = Field(default=False)
    enable_model_explainability_monitor: bool = Field(default=False)

    # Data quality monitoring options.
    data_quality_baseline_s3_uri: Optional[str] = Field(default="")
    data_quality_output_s3_uri: Optional[str] = Field(default="")
    data_quality_instance_count: int = Field(default=1, ge=1)
    data_quality_instance_type: str = Field(default="ml.m5.large")
    data_quality_instance_volume_size_in_gb: int = Field(default=20, ge=1)
    data_quality_max_runtime_in_seconds: int = Field(default=3600, ge=1)
    data_quality_schedule_expression: str = Field(default="cron(0 * ? * * *)")

    # Model quality monitoring options.
    model_quality_baseline_s3_uri: str = Field(default="")
    model_quality_output_s3_uri: str = Field(default="")
    model_quality_ground_truth_s3_uri: str = Field(default="")
    model_quality_instance_count: int = Field(default=1, ge=1)
    model_quality_instance_type: str = Field(default="ml.m5.large")
    model_quality_instance_volume_size_in_gb: int = Field(default=20, ge=1)
    model_quality_max_runtime_in_seconds: int = Field(default=1800, ge=1)
    model_quality_problem_type: str = Field(default="Regression")
    model_quality_inference_attribute: Optional[str] = Field(default=None)
    model_quality_probability_attribute: Optional[str] = Field(default=None)
    model_quality_probability_threshold_attribute: Optional[float] = Field(default=None)
    model_quality_schedule_expression: str = Field(default="cron(0 * ? * * *)")

    # Model bias monitoring options.
    model_bias_baseline_s3_uri: str = Field(default="")
    model_bias_analysis_s3_uri: Optional[str] = Field(default="")
    model_bias_output_s3_uri: str = Field(default="")
    model_bias_ground_truth_s3_uri: str = Field(default="")
    model_bias_instance_count: int = Field(default=1, ge=1)
    model_bias_instance_type: str = Field(default="ml.m5.large")
    model_bias_instance_volume_size_in_gb: int = Field(default=20, ge=1)
    model_bias_max_runtime_in_seconds: int = Field(default=1800, ge=1)
    model_bias_features_attribute: Optional[str] = Field(default=None)
    model_bias_inference_attribute: Optional[str] = Field(default=None)
    model_bias_probability_attribute: Optional[str] = Field(default=None)
    model_bias_probability_threshold_attribute: Optional[float] = Field(default=None)
    model_bias_schedule_expression: str = Field(default="cron(0 * ? * * *)")

    # Model explainability monitoring options.
    model_explainability_baseline_s3_uri: str = Field(default="")
    model_explainability_analysis_s3_uri: Optional[str] = Field(default=None)
    model_explainability_output_s3_uri: str = Field(default="")
    model_explainability_instance_count: int = Field(default=1, ge=1)
    model_explainability_instance_type: str = Field(default="ml.m5.large")
    model_explainability_instance_volume_size_in_gb: int = Field(default=20, ge=1)
    model_explainability_max_runtime_in_seconds: int = Field(default=1800, ge=1)
    model_explainability_features_attribute: Optional[str] = Field(default=None)
    model_explainability_inference_attribute: Optional[str] = Field(default=None)
    model_explainability_probability_attribute: Optional[str] = Field(default=None)
    model_explainability_schedule_expression: str = Field(default="cron(0 * ? * * *)")

    tags: Optional[Dict[str, str]] = Field(default=None)


class SeedFarmerSettings(CdkBaseSettings):
    """SeedFarmer Settings.

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
    """CDK default Settings.

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
