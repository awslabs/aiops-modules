# Custom Kernel Module

## Description

This module builds custom kernel for SageMaker studio from a Dockerfile.

## Inputs/Outputs

### Input Paramenters

#### Required

- `ecr_repo_name`: Name of the ECR repo for the image.
- `studio_domain_id`: SageMaker studio domain to attach the kernel to.
- `studio_domain_name`: SageMaker studio name to attach the kernel to.
- `sagemaker_image_name`: Name of the sagemaker image. This variable is also used to find the Dockerfile. The docker build script will be looking for file inside `modules/mlops/custom-kernel/docker/{sagemaker_image_name}`. 1 Dockerfile is added already: `pytorch-10`.
- `studio-execution-role-arn`: SageMaker Studio Domain execution role. Required to associate custom kernel with SageMaker Studio Domain.

#### Optional

- `app_image_config_name`:  Name of the app image config. Defaults to `idf-{deployment_name}-app-config`
- `kernel_user_uuid`: Default Unix User ID, defaults to: 1000
- `kernel_user_guid`: Default Unix Group ID, defaults to 100
- `kernel_user_mount_path`: # Path to mount in SageMaker Studio, defaults to `/home/sagemaker-user`

### Module Metadata Outputs

- `ECRRepositoryName`: ECR repository name
- `CustomKernelImageName`: Image name
- `CustomKernelImageURI`: Image URI
- `AppImageConfigName`: AppConfig image name
- `SageMakerCustomKernelRoleArn`: Role for custom kernel

#### Output Example

```json
{
    "ECRRepositoryName": "default",
    "CustomKernelImageName": "echo-kernel",
    "CustomKernelImageURI": "<account>.dkr.ecr.us-east-1.amazonaws.com/default:latest",
    "AppImageConfigName": "echo-kernel-app-config",
    "SageMakerCustomKernelRoleArn": "arn:aws:iam::<account>:role/idf-shared-infra-kernels-addfsharedinfrakernelske-9O6FZXGI0MM8",
}

```
