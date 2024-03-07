# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Provides utilities for SageMaker Pipeline CLI."""
from __future__ import absolute_import

import ast
from typing import Any, Dict, Optional


def get_pipeline_driver(module_name: str, passed_args: Optional[str] = None) -> Any:
    """Gets the driver for generating your pipeline definition.

    Pipeline modules must define a get_pipeline() module-level method.

    Args:
        module_name: The module name of your pipeline.
        passed_args: Optional passed arguments that your pipeline may be templated by.

    Returns:
        The SageMaker Workflow pipeline.
    """
    _imports = __import__(module_name, fromlist=["get_pipeline"])
    kwargs = convert_struct(passed_args)
    return _imports.get_pipeline(**kwargs)


def convert_struct(str_struct: Optional[str] = None) -> Any:
    """convert the string argument to it's proper type

    Args:
        str_struct (str, optional): string to be evaluated. Defaults to None.

    Returns:
        string struct as it's actuat evaluated type
    """
    return ast.literal_eval(str_struct) if str_struct else {}


def get_pipeline_custom_tags(module_name: str, args: Optional[str], tags: Dict[str, Any]) -> Any:
    """Gets the custom tags for pipeline

    Returns:
        Custom tags to be added to the pipeline
    """
    try:
        _imports = __import__(module_name, fromlist=["get_pipeline_custom_tags"])
        kwargs = convert_struct(args)
        return _imports.get_pipeline_custom_tags(tags, kwargs["region"], kwargs["sagemaker_project_arn"])
    except Exception as e:
        print(f"Error getting project tags: {e}")
    return tags
