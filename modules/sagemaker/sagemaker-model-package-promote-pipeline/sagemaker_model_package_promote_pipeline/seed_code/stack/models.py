"""Sagemaker Model Package models."""

from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer, model_serializer
from pydantic.alias_generators import to_camel
from pydantic.config import ConfigDict


class CdkBaseModel(BaseModel, ABC):
    """Defines common configuration for model."""

    model_config = ConfigDict(
        # alias_generator=to_pascal,
        populate_by_name=True,
        protected_namespaces=(),
        extra="ignore",
    )


class CdkModel(CdkBaseModel, ABC):
    """Defines common configuration for CdkModel."""

    @model_serializer
    def ser_model(self) -> Dict[str, Any]:
        """Convert field names to camelCase."""
        d = {to_camel(f): getattr(self, f) for f in self.model_fields.keys()}
        return d


class ModelPackageContainerDefinitionProperty(CdkModel):
    """ModelPackageContainerDefinitionProperty."""

    image: str = Field(alias="Image")

    container_hostname: Optional[str] = Field(default=None, alias="ContainerHostname")

    environment: Optional[Dict[str, str]] = Field(default=None, alias="Environment")

    framework: Optional[str] = Field(default=None, alias="Framework")
    framework_version: Optional[str] = Field(default=None, alias="FrameworkVersion")
    model_data_url: Optional[str] = Field(default=None, alias="ModelDataUrl")

    model_input: Optional[Any] = Field(default=None, alias="ModelInput")
    nearest_model_name: Optional[str] = Field(default=None, alias="NearestModelName")


class InferenceSpecificationProperty(CdkModel):
    """Inference Specification settings."""

    containers: List[ModelPackageContainerDefinitionProperty] = Field(alias="Containers")
    supported_content_types: List[str] = Field(alias="SupportedContentTypes")
    supported_response_mime_types: List[str] = Field(
        alias="SupportedResponseMIMETypes",
    )
    supported_realtime_inference_instance_types: Optional[List[str]] = Field(
        default=None,
        alias="SupportedRealtimeInferenceInstanceTypes",
    )
    supported_transform_instance_types: Optional[List[str]] = Field(
        default=None,
        alias="SupportedTransformInstanceTypes",
    )


class AdditionalInferenceSpecificationDefinitionProperty(InferenceSpecificationProperty):
    """AdditionalInferenceSpecificationDefinitionProperty."""

    name: str = Field(alias="Name")
    description: Optional[str] = Field(default=None, alias="Description")


class MetricsSourceProperty(CdkModel):
    """MetricsSourceProperty."""

    s3_uri: str = Field(alias="S3Uri")
    content_type: str = Field(alias="ContentType")


class FileSourceProperty(CdkModel):
    """FileSourceProperty."""

    s3_uri: str = Field(alias="S3Uri")
    content_type: Optional[str] = Field(default=None, alias="ContentType")


class DriftCheckBiasProperty(CdkModel):
    """DriftCheckBiasProperty."""

    config_file: Optional[FileSourceProperty] = Field(default=None, alias="ConfigFile")
    post_training_constraints: Optional[MetricsSourceProperty] = Field(
        default=None,
        alias="PostTrainingConstraints",
    )
    pre_training_constraints: Optional[MetricsSourceProperty] = Field(
        default=None,
        alias="PreTrainingConstraints",
    )


class DriftCheckExplainabilityProperty(CdkModel):
    """DriftCheckExplainabilityProperty."""

    config_file: Optional[FileSourceProperty] = Field(default=None, alias="ConfigFile")
    constraints: Optional[MetricsSourceProperty] = Field(default=None, alias="Constraints")


class DriftCheckModelDataQualityProperty(CdkModel):
    """DriftCheckModelDataQualityProperty."""

    constraints: Optional[MetricsSourceProperty] = Field(default=None, alias="Constraints")
    statistics: Optional[MetricsSourceProperty] = Field(default=None, alias="Statistics")


class DriftCheckModelQualityProperty(CdkModel):
    """DriftCheckModelQualityProperty."""

    constraints: Optional[MetricsSourceProperty] = Field(default=None, alias="Constraints")
    statistics: Optional[MetricsSourceProperty] = Field(default=None, alias="Statistics")


class DriftCheckBaselinesProperty(CdkModel):
    """DriftCheckBaselinesProperty."""

    bias: Optional[DriftCheckBiasProperty] = Field(default=None, alias="Bias")
    explainability: Optional[DriftCheckExplainabilityProperty] = Field(default=None, alias="Explainability")
    model_data_quality: Optional[DriftCheckModelDataQualityProperty] = Field(default=None, alias="ModelDataQuality")
    model_quality: Optional[DriftCheckModelQualityProperty] = Field(default=None, alias="ModelQuality")


class MetadataPropertiesProperty(CdkModel):
    """MetadataPropertiesProperty."""

    commit_id: Optional[str] = Field(default=None, alias="CommitId")
    generated_by: Optional[str] = Field(default=None, alias="GeneratedBy")
    project_id: Optional[str] = Field(default=None, alias="ProjectId")
    repository: Optional[str] = Field(default=None, alias="Repository")


class BiasProperty(CdkModel):
    """BiasProperty."""

    post_training_report: Optional[MetricsSourceProperty] = Field(
        default=None,
        alias="PostTrainingReport",
    )
    pre_training_report: Optional[MetricsSourceProperty] = Field(default=None, alias="PreTrainingReport")
    report: Optional[MetricsSourceProperty] = Field(default=None, alias="Report")


class ExplainabilityProperty(CdkModel):
    """ExplainabilityProperty."""

    report: Optional[MetricsSourceProperty] = Field(default=None, alias="Report")


class ModelDataQualityProperty(CdkModel):
    """ModelDataQualityProperty."""

    constraints: Optional[MetricsSourceProperty] = Field(default=None, alias="Constraints")
    statistics: Optional[MetricsSourceProperty] = Field(default=None, alias="Statistics")


class ModelQualityProperty(CdkModel):
    """ModelQualityProperty."""

    constraints: Optional[MetricsSourceProperty] = Field(default=None, alias="Constraints")
    statistics: Optional[MetricsSourceProperty] = Field(default=None, alias="Statistics")


class ModelMetricsProperty(CdkModel):
    """ModelMetricsProperty."""

    bias: Optional[BiasProperty] = Field(default=None, alias="Bias")
    explainability: Optional[ExplainabilityProperty] = Field(default=None, alias="Explainability")
    model_data_quality: Optional[ModelDataQualityProperty] = Field(default=None, alias="ModelDataQuality")
    model_quality: Optional[ModelQualityProperty] = Field(default=None, alias="ModelQuality")


class ModelPackageStatusItemProperty(CdkModel):
    """ModelPackageStatusItemProperty."""

    name: str = Field(alias="Name")
    status: str = Field(alias="Status")
    failure_reason: Optional[str] = Field(default=None, alias="FailureReason")


class ModelPackageStatusDetailsProperty(CdkModel):
    """ModelPackageStatusDetailsProperty."""

    validation_statuses: Optional[List[ModelPackageStatusItemProperty]] = Field(
        default=None,
        alias="ValidationStatuses",
    )


class SourceAlgorithmProperty(CdkModel):
    """SourceAlgorithmProperty."""

    algorithm_name: str = Field(alias="AlgorithmName")
    model_data_url: Optional[str] = Field(default=None, alias="ModelDataUrl")


class SourceAlgorithmSpecificationProperty(CdkModel):
    """SourceAlgorithmSpecificationProperty."""

    source_algorithms: List[SourceAlgorithmProperty] = Field(alias="SourceAlgorithms")


class S3DataSourceProperty(CdkModel):
    """S3DataSourceProperty."""

    s3_data_type: str = Field(alias="S3DataType")
    s3_uri: str = Field(alias="S3Uri")


class DataSourceProperty(CdkModel):
    """DataSourceProperty."""

    s3_data_source: Optional[S3DataSourceProperty] = Field(default=None, alias="S3DataSource")


class TransformInputProperty(CdkModel):
    """TransformInputProperty."""

    data_source: Optional[DataSourceProperty] = Field(default=None, alias="DataSource")
    compression_type: Optional[str] = Field(default=None, alias="CompressionType")
    content_type: Optional[str] = Field(default=None, alias="ContentType")
    split_type: Optional[str] = Field(default=None, alias="SplitType")


class TransformOutputProperty(CdkModel):
    """TransformOutputProperty."""

    s3_output_path: str = Field(alias="S3OutputPath")
    accept: Optional[str] = Field(default=None, alias="Accept")
    assemble_with: Optional[str] = Field(default=None, alias="AssembleWith")
    kms_key_id: Optional[str] = Field(default=None, alias="KmsKeyId")


class TransformResourcesProperty(CdkModel):
    """TransformResourcesProperty."""

    instance_count: int = Field(alias="InstanceCount")
    instance_type: str = Field(alias="InstanceType")
    volume_kms_key_id: Optional[str] = Field(default=None, alias="VolumeKmsKeyId")


class TransformJobDefinitionProperty(CdkModel):
    """TransformJobDefinitionProperty."""

    transform_input: Optional[TransformInputProperty] = Field(default=None, alias="TransformInput")
    transform_output: Optional[TransformOutputProperty] = Field(default=None, alias="TransformOutput")
    transform_resources: Optional[TransformResourcesProperty] = Field(
        default=None,
        alias="TransformResources",
    )
    batch_strategy: Optional[str] = Field(default=None, alias="BatchStrategy")
    environment: Optional[Dict[str, str]] = Field(default=None, alias="Environment")
    max_concurrent_transforms: Optional[int] = Field(
        default=None,
        alias="MaxConcurrentTransforms",
    )
    max_payload_in_mb: Optional[int] = Field(default=None, alias="MaxPayloadInMB")


class ValidationProfileProperty(CdkModel):
    """ValidationProfileProperty."""

    profile_name: str = Field(alias="ProfileName")
    transform_job_definition: TransformJobDefinitionProperty = Field(alias="TransformJobDefinition")


class ValidationSpecificationProperty(CdkModel):
    """ValidationSpecificationProperty."""

    validation_profiles: List[ValidationProfileProperty] = Field(alias="ValidationProfiles")
    validation_role: str = Field(alias="ValidationRole")


class ModelPackageProperty(CdkBaseModel):
    """Model Package settings."""

    model_package_name: Optional[str] = Field(default=None, alias="ModelPackageName")
    model_package_group_name: Optional[str] = Field(default=None, alias="ModelPackageGroupName")
    model_package_version: Optional[int] = Field(default=None, alias="ModelPackageVersion")
    model_package_description: Optional[str] = Field(default=None, alias="ModelPackageDescription")

    inference_specification: Optional[InferenceSpecificationProperty] = Field(
        default=None, alias="InferenceSpecification"
    )

    additional_inference_specifications: Optional[List[AdditionalInferenceSpecificationDefinitionProperty]] = Field(
        default=None, alias="AdditionalInferenceSpecifications"
    )
    approval_description: Optional[str] = Field(default=None, alias="ApprovalDescription")
    certify_for_marketplace: Optional[bool] = Field(default=None, alias="CertifyForMarketplace")
    customer_metadata_properties: Optional[Dict[str, str]] = Field(default=None, alias="CustomerMetadataProperties")
    domain: Optional[str] = Field(default=None, alias="Domain")
    drift_check_baselines: Optional[DriftCheckBaselinesProperty] = Field(default=None, alias="DriftCheckBaselines")
    last_modified_time: Optional[datetime] = Field(default=None, alias="LastModifiedTime")

    metadata_properties: Optional[MetadataPropertiesProperty] = Field(default=None, alias="MetadataProperties")
    model_approval_status: Optional[str] = Field(default=None, alias="ModelApprovalStatus")
    model_metrics: Optional[ModelMetricsProperty] = Field(default=None, alias="ModelMetrics")
    model_package_status_details: Optional[ModelPackageStatusDetailsProperty] = Field(
        default=None, alias="ModelPackageStatusDetails"
    )
    sample_payload_url: Optional[str] = Field(default=None, alias="SamplePayloadUrl")
    source_algorithm_specification: Optional[SourceAlgorithmSpecificationProperty] = Field(
        default=None, alias="SourceAlgorithmSpecification"
    )
    task: Optional[str] = Field(default=None, alias="Task")
    validation_specification: Optional[ValidationSpecificationProperty] = Field(
        default=None, alias="ValidationSpecification"
    )

    @field_serializer("last_modified_time")
    def serialize_last_modified_time(self, dt: Optional[datetime], _info: Any) -> Optional[str]:
        """Convert datetime to string."""
        return dt.isoformat() if dt else None


class ModelMetadata(CdkBaseModel):
    """Model metadata settings."""

    artifacts: str = Field(alias="Artifacts")
    model: ModelPackageProperty = Field(alias="Model")
