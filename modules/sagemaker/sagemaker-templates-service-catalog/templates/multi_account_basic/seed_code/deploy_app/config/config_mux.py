# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from abc import ABCMeta
from pathlib import Path
from typing import Any

import constructs
from aws_cdk import Stack, Stage
from dataclasses import dataclass
from yamldataclassconfig.config import YamlDataClassConfig

DEFAULT_STAGE_NAME = "dev"
DEFAULT_STACK_NAME = "dev"


def get_config_for_stage(scope: constructs.Construct, path: str) -> Any:
    default_path = Path(__file__).parent.joinpath(DEFAULT_STAGE_NAME, path)
    if stage_name := Stage.of(scope).stage_name:  # type: ignore[union-attr]
        config_path = Path(__file__).parent.joinpath(stage_name.lower(), path)

        if not config_path.exists():
            print(f"Config file {path} for stage {stage_name} not found. Using {default_path} instead")
            config_path = default_path

        return config_path
    else:
        print(f"Stack created without a stage, config {path} not found. Using {default_path} instead")
        return default_path


def get_config_for_stack(scope: constructs.Construct, path: str) -> Path:
    default_path = Path(__file__).parent.joinpath(DEFAULT_STACK_NAME, path)
    if stack_name := Stack.of(scope).stack_name:
        config_path = Path(__file__).parent.joinpath(stack_name.lower(), path)

        if not config_path.exists():
            print(f"Config file {path} for stack {stack_name} not found. Using {default_path} instead")
            config_path = default_path

        return config_path
    else:
        print(f"Stack created without a stack, config {path} not found. Using {default_path} instead")
        return default_path


@dataclass
class StageYamlDataClassConfig(YamlDataClassConfig, metaclass=ABCMeta):  # type:ignore[misc]
    """This class implements YAML file load function with relative config
    paths and stage specific config loading capabilities."""

    def load(self) -> Any:
        """
        This method automatically uses the config from alpha
        """
        path = Path(__file__).parent.joinpath("config/", "dev", self.FILE_PATH)
        return super().load(path=path)

    def load_for_stage(self, scope: constructs.Construct) -> Any:
        """
        Looks up the stage from the current scope and loads the relevant config file
        """
        path = get_config_for_stage(scope, self.FILE_PATH)
        return super().load(path=path)

    def load_for_stack(self, scope: constructs.Construct) -> Any:
        """
        Looks up the stack from the current scope and loads the relevant config file
        """
        path = get_config_for_stack(scope, self.FILE_PATH)
        return super().load(path=path)
