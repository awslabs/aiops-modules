"""Defines the stack settings."""

from abc import ABC
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectTemplateType(str, Enum):
    """Available project template types."""

    XGBOOST_ABALONE = "xgboost_abalone"
    BATCH_INFERENCE = "batch_inference"
    FINETUNE_LLM_EVALUATION = "finetune_llm_evaluation"
    HF_IMPORT_MODELS = "hf_import_models"
    MODEL_DEPLOY = "model_deploy"


class RepositoryType(str, Enum):
    """Repository type for source code."""

    CODECOMMIT = "CodeCommit"
    GITHUB = "GitHub"
    GITHUB_ENTERPRISE = "GitHub Enterprise"


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

    project_template_type: ProjectTemplateType

    sagemaker_domain_id: Optional[str] = Field(default=None)
    sagemaker_domain_arn: Optional[str] = Field(default=None)
    sagemaker_project_name: str
    sagemaker_project_id: str

    dev_vpc_id: Optional[str] = Field(default=None)
    dev_subnet_ids: List[str] = Field(default=[])
    dev_security_group_ids: List[str] = Field(default=[])

    pre_prod_account_id: Optional[str] = Field(default=None)
    pre_prod_region: Optional[str] = Field(default=None)
    pre_prod_vpc_id: Optional[str] = Field(default=None)
    pre_prod_subnet_ids: List[str] = Field(default=[])
    pre_prod_security_group_ids: List[str] = Field(default=[])

    prod_account_id: Optional[str] = Field(default=None)
    prod_region: Optional[str] = Field(default=None)
    prod_vpc_id: Optional[str] = Field(default=None)
    prod_subnet_ids: List[str] = Field(default=[])
    prod_security_group_ids: List[str] = Field(default=[])

    repository_type: RepositoryType = Field(default=RepositoryType.CODECOMMIT)
    access_token_secret_name: str = Field(default="github_token")
    aws_codeconnection_arn: Optional[str] = Field(default=None)
    repository_owner: Optional[str] = Field(default=None)

    tags: Optional[Dict[str, str]] = Field(default=None)


class XGBoostAbaloneProjectSettings(CdkBaseSettings):
    """XGBoost Abalone Project Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    enable_network_isolation: bool = Field(default=False)
    encrypt_inter_container_traffic: bool = Field(default=False)


class ModelDeployProjectSettings(CdkBaseSettings):
    """Model Deploy Project Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    model_package_group_name: str
    model_bucket_name: str
    enable_network_isolation: bool = Field(default=False)


class HfImportModelsProjectSettings(CdkBaseSettings):
    """Hf Import Models Project Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    hf_access_token_secret: str
    hf_model_id: str


class BatchInferenceProjectSettings(CdkBaseSettings):
    """Batch Inference Project Parameters.

    These parameters are required for the module stack.
    """

    model_config = SettingsConfigDict(env_prefix="SEEDFARMER_PARAMETER_")

    model_package_group_name: str
    model_bucket_name: str
    base_job_prefix: str


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

    xgboost_abalone_project_settings: Optional[XGBoostAbaloneProjectSettings] = Field(default=None)
    model_deploy_project_settings: Optional[ModelDeployProjectSettings] = Field(default=None)
    hf_import_models_project_settings: Optional[HfImportModelsProjectSettings] = Field(default=None)
    batch_inference_project_settings: Optional[BatchInferenceProjectSettings] = Field(default=None)

    @model_validator(mode="after")
    def initialize_project_settings(self: Any) -> None:
        template_type = self.module_settings.project_template_type

        if template_type == ProjectTemplateType.XGBOOST_ABALONE and self.xgboost_abalone_project_settings is None:
            self.xgboost_abalone_project_settings = XGBoostAbaloneProjectSettings()
        elif template_type == ProjectTemplateType.MODEL_DEPLOY and self.model_deploy_project_settings is None:
            self.model_deploy_project_settings = ModelDeployProjectSettings()
        elif template_type == ProjectTemplateType.HF_IMPORT_MODELS and self.hf_import_models_project_settings is None:
            self.hf_import_models_project_settings = HfImportModelsProjectSettings()
        elif template_type == ProjectTemplateType.BATCH_INFERENCE and self.batch_inference_project_settings is None:
            self.batch_inference_project_settings = BatchInferenceProjectSettings()
