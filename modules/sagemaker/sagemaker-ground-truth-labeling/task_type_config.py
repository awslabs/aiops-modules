from typing import Dict, List, Optional, Union

DEFAULT_LABELING_ATTRIBUTE_NAME = "label"
DEFAULT_VERIFICATION_ATTRIBUTE_NAME = "verification"

# Certain jobs require the attribute end with -ref
ALTERNATIVE_LABELING_ATTRIBUTE_NAME = DEFAULT_LABELING_ATTRIBUTE_NAME + "-ref"

METADATA = "-metadata"

IMAGE = "image"
TEXT = "text"

IMAGE_SOURCE_KEY = "source-ref"
TEXT_SOURCE_KEY = "source"


class UndefinedTaskTypeError(Exception):
    pass


class FeatureDefinitionConfig:
    def __init__(
        self,
        feature_name: str,
        feature_type: str,
        output_key: List[Union[str, int]],
    ):
        self.feature_name = feature_name
        self.feature_type = feature_type
        self.output_key = output_key


class TaskTypeConfig:
    def __init__(
        self,
        task_type: str,
        media_type: str,
        source_key: str,
        function_name: str,
        labeling_attribute_name: str,
        feature_group_config: List[FeatureDefinitionConfig],
        verification_attribute_name: Optional[str] = None,
    ):
        self.task_type = task_type
        self.media_type = media_type
        self.source_key = source_key
        self.function_name = function_name
        self.labeling_attribute_name = labeling_attribute_name
        self.verification_attribute_name = verification_attribute_name
        self.feature_group_config = feature_group_config


class TaskTypeConfigManager:
    def __init__(self) -> None:
        self.configs: Dict[str, TaskTypeConfig] = {}

    def add_config(self, config: TaskTypeConfig) -> None:
        self.configs[config.task_type] = config

    def get_config(self, task_type: str) -> TaskTypeConfig:
        if task_type not in self.configs:
            raise UndefinedTaskTypeError(f"Task type '{task_type}' is not defined")
        return self.configs[task_type]


task_type_manager = TaskTypeConfigManager()

task_type_manager.add_config(
    TaskTypeConfig(
        task_type="image_bounding_box",
        media_type=IMAGE,
        source_key=IMAGE_SOURCE_KEY,
        function_name="BoundingBox",
        labeling_attribute_name=DEFAULT_LABELING_ATTRIBUTE_NAME,
        feature_group_config=[
            FeatureDefinitionConfig(
                "image_width",
                "Integral",
                [DEFAULT_LABELING_ATTRIBUTE_NAME, "image_size", 0, "width"],
            ),
            FeatureDefinitionConfig(
                "image_height",
                "Integral",
                [DEFAULT_LABELING_ATTRIBUTE_NAME, "image_size", 0, "height"],
            ),
            FeatureDefinitionConfig(
                "image_depth",
                "Integral",
                [DEFAULT_LABELING_ATTRIBUTE_NAME, "image_size", 0, "depth"],
            ),
            FeatureDefinitionConfig(
                "annotations",
                "String",
                [DEFAULT_LABELING_ATTRIBUTE_NAME, "annotations"],
            ),
            FeatureDefinitionConfig(
                "class_map",
                "String",
                [DEFAULT_LABELING_ATTRIBUTE_NAME + METADATA, "class-map"],
            ),
            FeatureDefinitionConfig(
                "objects",
                "String",
                [DEFAULT_LABELING_ATTRIBUTE_NAME + METADATA, "objects"],
            ),
        ],
        verification_attribute_name=DEFAULT_VERIFICATION_ATTRIBUTE_NAME,
    )
)

task_type_manager.add_config(
    TaskTypeConfig(
        task_type="image_semantic_segmentation",
        media_type=IMAGE,
        source_key=IMAGE_SOURCE_KEY,
        function_name="SemanticSegmentation",
        labeling_attribute_name=ALTERNATIVE_LABELING_ATTRIBUTE_NAME,
        feature_group_config=[
            FeatureDefinitionConfig(
                "image_location",
                "String",
                [ALTERNATIVE_LABELING_ATTRIBUTE_NAME],
            ),
            FeatureDefinitionConfig(
                "internal_color_map",
                "String",
                [ALTERNATIVE_LABELING_ATTRIBUTE_NAME + METADATA, "internal-color-map"],
            ),
        ],
        verification_attribute_name=DEFAULT_VERIFICATION_ATTRIBUTE_NAME,
    )
)

single_label_classification_feature_group_config = [
    FeatureDefinitionConfig(
        "class_name",
        "String",
        [DEFAULT_LABELING_ATTRIBUTE_NAME + METADATA, "class-name"],
    ),
    FeatureDefinitionConfig(
        "confidence",
        "Fractional",
        [DEFAULT_LABELING_ATTRIBUTE_NAME + METADATA, "confidence"],
    ),
]

task_type_manager.add_config(
    TaskTypeConfig(
        task_type="image_single_label_classification",
        media_type=IMAGE,
        source_key=IMAGE_SOURCE_KEY,
        function_name="ImageMultiClass",
        labeling_attribute_name=DEFAULT_LABELING_ATTRIBUTE_NAME,
        feature_group_config=single_label_classification_feature_group_config,
    )
)

task_type_manager.add_config(
    TaskTypeConfig(
        task_type="text_single_label_classification",
        media_type=TEXT,
        source_key=TEXT_SOURCE_KEY,
        function_name="TextMultiClass",
        labeling_attribute_name=DEFAULT_LABELING_ATTRIBUTE_NAME,
        feature_group_config=single_label_classification_feature_group_config,
    )
)

multi_label_classification_feature_group_config = [
    FeatureDefinitionConfig(
        "classes",
        "String",
        [DEFAULT_LABELING_ATTRIBUTE_NAME],
    ),
    FeatureDefinitionConfig(
        "class_map",
        "String",
        [DEFAULT_LABELING_ATTRIBUTE_NAME + METADATA, "class-map"],
    ),
    FeatureDefinitionConfig(
        "confidence_map",
        "String",
        [DEFAULT_LABELING_ATTRIBUTE_NAME + METADATA, "confidence-map"],
    ),
]

task_type_manager.add_config(
    TaskTypeConfig(
        task_type="image_multi_label_classification",
        media_type=IMAGE,
        source_key=IMAGE_SOURCE_KEY,
        function_name="ImageMultiClassMultiLabel",
        labeling_attribute_name=DEFAULT_LABELING_ATTRIBUTE_NAME,
        feature_group_config=multi_label_classification_feature_group_config,
    )
)

task_type_manager.add_config(
    TaskTypeConfig(
        task_type="text_multi_label_classification",
        media_type=TEXT,
        source_key=TEXT_SOURCE_KEY,
        function_name="TextMultiClassMultiLabel",
        labeling_attribute_name=DEFAULT_LABELING_ATTRIBUTE_NAME,
        feature_group_config=multi_label_classification_feature_group_config,
    )
)

task_type_manager.add_config(
    TaskTypeConfig(
        task_type="named_entity_recognition",
        media_type=TEXT,
        source_key=TEXT_SOURCE_KEY,
        function_name="NamedEntityRecognition",
        labeling_attribute_name=DEFAULT_LABELING_ATTRIBUTE_NAME,
        feature_group_config=[
            FeatureDefinitionConfig(
                "annotations",
                "String",
                [DEFAULT_LABELING_ATTRIBUTE_NAME, "annotations"],
            ),
            FeatureDefinitionConfig(
                "entities_confidence",
                "String",
                [DEFAULT_LABELING_ATTRIBUTE_NAME + METADATA, "entities"],
            ),
        ],
    )
)


def get_task_type_config(task_type: str) -> TaskTypeConfig:
    return task_type_manager.get_config(task_type)
