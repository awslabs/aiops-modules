# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

=======

## UNRELEASED

### **Added**

- added SSO support in `sagemaker-studio` module
- added VPC/subnets/sg config for multi-account project template to `sagemaker-templates-service-catalog` module
- added `sagemaker-custom-kernel` module
- added batch inference project template to `sagemaker-templates-service-catalog` module
- added EFS removal policy to `mlflow-fargate` module
- added `mwaa` module with example dag which demonstrates the MLOps in Airflow
- added `sagemaker-hugging-face-endpoint` module

### **Changed**

- add account/region props for project templates in `sagemaker-templates-service-catalog` module
- fix `sagemaker-templates-service-catalog` model deploy role lookup issue & abalone_xgboost model registry permissions
- update `sagemaker-custom-kernel` module IAM permissions
- split `xgboost_abalone` and `model_deploy` project templates in `sagemaker-templates-service-catalog` module
- add support for other AWS partitions
- update MySQL instance to use T3 instance type
- upgrade `cdk_ecr_deployment` version to fix the deprecated `go1.x` lambda runtime

### **Removed**

- remove AmazonSageMakerFullAccess from `multi_account_basic` template in the `sagemaker-templates-service-catalog` module
- remove AmazonSageMakerFullAccess from `sagemaker-endpoint` module

## v1.0.0

### **Added**

- added `sagemaker-templates-service-catalog` module with `multi_account_basic` project template
- bump cdk & ecr deployment version to fix deprecated custom resource runtimes issue in `mlflow-image`
- added `sagemaker-jumpstart-fm-endpoint` module
- added RDS persistence layer to MLFlow modules
- added `mlflow-image` and `mlflow-fargate` modules
- added `sagemaker-studio` module
- added `sagemaker-endpoint` module
- added `sagemaker-notebook` module

### **Changed**

- refactor validation script to use `ruff` instead of `black` and `isort`

### **Removed**
