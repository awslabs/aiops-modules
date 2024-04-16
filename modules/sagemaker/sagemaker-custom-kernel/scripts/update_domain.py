# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import boto3

# Seed-Farmer Variables
project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")

# Module Parameters
image_name = os.getenv("SEEDFARMER_PARAMETER_SAGEMAKER_IMAGE_NAME", "echo-kernel")
app_image_config_name = os.getenv("SEEDFARMER_PARAMETER_APP_IMAGE_CONFIG_NAME", "echo-kernel")
sm_studio_domain_id = os.environ.get("SEEDFARMER_PARAMETER_STUDIO_DOMAIN_ID")
sm_studio_domain_name = os.environ.get("SEEDFARMER_PARAMETER_STUDIO_DOMAIN_NAME")

# Config vars
display_name = image_name  # Should stay same to allow config mapping in update_domain
sm_client = boto3.client("sagemaker")


def update_domain():
    try:
        domain = sm_client.describe_domain(
            DomainId=sm_studio_domain_id,
        )

        print("current_domain", domain)

        default_user_settings = domain["DefaultUserSettings"]
        if "KernelGatewayAppSettings" not in default_user_settings:
            default_user_settings["KernelGatewayAppSettings"] = {}
        kernel_gateway_app_settings = default_user_settings["KernelGatewayAppSettings"]
        existing_custom_images = kernel_gateway_app_settings.get("CustomImages", [])

        # Custom Image config we'd like to attach to Studio
        new_custom_image = {
            "ImageName": display_name,
            "AppImageConfigName": app_image_config_name,
        }

        existing_custom_images.append(new_custom_image)
        merged_distinct_custom_images = list(
            dict((v["AppImageConfigName"], v) for v in existing_custom_images).values(),
        )
        default_user_settings["KernelGatewayAppSettings"]["CustomImages"] = merged_distinct_custom_images

        print(f"Updating Sagemaker Studio Domain - {sm_studio_domain_name} ({sm_studio_domain_id})")
        print(default_user_settings)
        sm_client.update_domain(
            DomainId=sm_studio_domain_id,
            DefaultUserSettings=default_user_settings,
        )
    except Exception as e:
        print("Error updating studio domain")
        raise e


def print_step(step):
    print(f'{"-" * 35} {step} {"-" * 35}')


if __name__ == "__main__":
    update_domain()
    print_step("Update Domain Complete")
