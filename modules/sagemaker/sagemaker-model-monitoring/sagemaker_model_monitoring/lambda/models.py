from typing import List, Optional

from pydantic import BaseModel, Field


class BaseParams(BaseModel):
    instance_count: int = Field(default=1, ge=1, description="Number of ML compute instances")
    instance_type: str = Field(default="ml.m5.large", description="ML compute instance type")
    volume_size_gb: int = Field(default=20, ge=1, description="Size of ML storage volume in GB")
    max_runtime_seconds: int = Field(default=1800, ge=1, description="Maximum runtime in seconds")


class DataQualityParams(BaseParams):
    max_runtime_seconds: int = Field(default=3600, ge=1, description="Maximum runtime in seconds")


class ModelQualityParams(BaseParams):
    problem_type: str = Field(default="BinaryClassification", description="ML problem type")
    inference_attribute: str = Field(default="prediction", description="Inference attribute name")
    probability_attribute: str = Field(default="probability", description="Probability attribute name")
    ground_truth_attribute: str = Field(default="label", description="Ground truth attribute name")


class ModelBiasParams(BaseParams):
    label_header: str = Field(default="label", description="Label column header")
    headers: str = Field(default="", description="Comma-separated headers")
    dataset_type: str = Field(default="text/csv", description="Dataset content type")
    label_values: str = Field(default="1", description="Comma-separated label values")
    facet_name: str = Field(default="Account Length", description="Bias facet name")
    facet_values: str = Field(default="100", description="Comma-separated facet values")
    probability_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Probability threshold")
    model_name: Optional[str] = Field(default=None, description="Model name")

    def get_label_values(self) -> List[int]:
        return [int(x.strip()) for x in self.label_values.split(",")]

    def get_facet_values(self) -> List[int]:
        return [int(x.strip()) for x in self.facet_values.split(",")]

    def get_headers(self) -> Optional[List[str]]:
        return [h.strip() for h in self.headers.split(",")] if self.headers else None


class ModelExplainabilityParams(BaseParams):
    label_header: str = Field(default="label", description="Label column header")
    headers: str = Field(default="", description="Comma-separated headers")
    dataset_type: str = Field(default="text/csv", description="Dataset content type")
    model_name: Optional[str] = Field(default=None, description="Model name")
    num_samples: int = Field(default=100, ge=1, description="Number of samples for SHAP")
    agg_method: str = Field(default="mean_abs", description="SHAP aggregation method")
    save_local_shap_values: bool = Field(default=False, description="Save local SHAP values")
    shap_baseline: List[List[float]] = Field(default=[[0.0]], description="SHAP baseline values")

    def get_headers(self) -> Optional[List[str]]:
        return [h.strip() for h in self.headers.split(",")] if self.headers else None
