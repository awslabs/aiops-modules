# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## UNRELEASED

### **Added**

### **Changed**

## v1.7.1

### **Added**
- added `mlflow-ai-gw-image` module

### **Changed**
- changed `ray-image` to pull from AWS Public ECR to avoid docker pull rate limits
- changed `ray-orchestrator` to not retrieve full training job logs and avoid `States.DataLimitExceeded`
- update `ray-on-eks` manifest cluster resources
- update ray operator to use kubectl handler role

## v1.7.0

### **Added**
- added GitHub as code repository option along with AWS CodeCommit for sagemaker templates batch_inference, finetune_llm_evaluation, hf_import_models and xgboost_abalone
- added `ray-orchestrator` module
- added GitHub as alternate option for code repository support along with AWS CodeCommit for sagemaker-templates-service-catalog module
- added SageMaker ground truth labeling module

### **Changed**
- updated manifests to idf release 1.12.0

## v1.6.0

### **Added**
- added new manifest `manifests/fine-tuning-6B`

### **Changed**

- updated mlflow version to 2.16.0 to support LLM tracing
- remove CDK overhead from `mlflow-image` module
- renamed mlflow manifests and updated README.MD
- added head tolerations & node labels for flexible ray cluster pods scheduling

## v1.5.0

### **Added**
- added documentation for MWAA Sagemaker training DAG manifest
- added documentation for Ray on EKS manifests
- added network isolation and inter container encryption for xgboost template
- added partition support for modules:
  - `fmops/sagemaker-jumpstart-fm-endpoint`
  - `sagemaker/sagemaker-endpoint`
  - `sagemaker/sagemaker-notebook`
  - `sagemaker/sagemaker-studio`
- added Bedrock fine-tuning manifest

### **Changed**
- added accelerate as extra for transformers in finetune llm template
- limited bucket name length in templates to avoid pipeline failures when using long project names
- increased timeout on finetune_llm_evaluation project from 1 hour (default) to 4 hours
- pin `ray-operator`, `ray-cluster`, and `ray-image` modules versions
- pin module versions for all manifests
- the `sagemaker/sagemaker-model-package-promote-pipeline` module no longer generates a Docker image
- lowercase `fine-tuning-6b` deployment name due to CDK resource naming constraints

## v1.4.0

### **Added**

- adds workflow specific to changes for `requirements-dev.txt` so all static checks are run
- add `ray-cluster` module based on `kuberay-helm` charts
- added FSx for Lustre to `ray-on-eks` manifest & persistent volume claim to `ray-cluster` module
- added worker tolerations to `ray-cluster` module

### **Changed**

- add integration tests for `sagemaker-studio`
- bump ecr module version to 1.10.0 to consume auto-delete images feature
- add service account to kuberay
- updated `get-modules` workflow to only run tests against changed files in `modules/**`
- Updated the `sagemaker-templates-service-catalog` module documentation to match the code layout.
- Modernize `sagemaker-templates-service-catalog` packaging and remove unused dependencies.
- remove custom manifests via `dataFiles` from `ray-on-eks`
- refactor `ray-on-eks` to `ray-cluster` and `ray-operator` modules
- downscope `ray-operator` service account permissions
- add an example custom `ray-image`
- document available manifests in readme
- add permission for SM studio to describe apps when domain resource isolation is enabled
- updated `ray-on-eks` manifest to use latest EKS IDF release

## v1.3.0

### **Added**

- added `ray-on-eks`, and `manifests/ray-on-eks` manifests
- added a `sagemaker-model-monitoring-module` module with an example of data quality, model quality, model bias, and model explainability monitoring of a SageMaker Endpoint
- added an option to enable data capture in the `sagemaker-endpoint-module`
- added a `personas` example module to deploy various roles required for an AI/ML project
- added `sagemaker-model-cicd` module
- added `sagemaker_domain_arn` as optional input for multiple modules, tags resources created with domain ARN to support domain resource isolation
- added `enable_network_isolation` as optional input for `sagemaker-endpoint` module, defaults to true
- added `enable_domain_resource_isolation` as optional input for `sagemaker-studio` module, adds IAM policy to studio roles preventing the access of resources from outside the domain, defaults to true
- added `StudioDomainArn` as output from `sagemaker-studio` module
- added `enable_network_isolation` as parameter for `model_deploy` template

### **Changed**

- remove explicit module manifest account/region mappings from `fmops-qna-rag`
- moved CI/CD infra to separate repository and added self mutation pipeline to provision infra for module `sagemaker-templates-service-catalog`
- changed ECR encryption to KMS_MANAGED
- changed encryption for each bucket to KMS_MANAGED
- refactor `airflow-dags` module to use Pydantic
- fix inputs for `bedrock-finetuning` module not working
- add `retention-type` argument for the bucket in the `bedrock-finetuning` module
- fix broken dependencies for `examples/airflow-dags`
- use `add_dependency` to avoid deprecation warnings from CDK
- various typo fixes
- various clean-ups to the SageMaker Service Catalog templates
- fix opensearch removal policy
- update MWAA to 2.9.2
- update mwaa constraints
- limit length of id in model name to prevent model name becoming too long
- add permission for get secret value in `hf_import_models` template
- add manifests/tags parameters to one-click-template
- add integration tests for `mlflow-image`

## v1.2.0

### **Added**

- added multi-acc sagemaker-mlops manifest example

### **Changed**

- fixed model deploy cross-account permissions
- added bucket and model package group names as stack outputs in the `sagemaker-templates` module
- refactor inputs for the following modules to use Pydantic:
  - `mlflow-fargate`
  - `mlflow-image`
  - `sagemaker-studio`
  - `sagemaker-endpoint`
  - `sagemaker-templates-service-catalog`
  - `sagemaker-custom-kernel`
  - `qna-rag`
- add CDK nag to `qna-rag` module
- rename seedfarmer project name to `aiops`
- chore: adding some missing auto_delete attributes
- chore: Add `auto_delete` to `mlflow-fargate` elb access logs bucket
- updating `storage/ecr` module to latest pending `v1.8.0` of IDF
- enabled ECR image scan on push

## v1.1.0

### **Added**

- added managed autoscaling config to `sagemaker-endpoint` module
- added SSO support in `sagemaker-studio` module
- added VPC/subnets/sg config for multi-account project template to `sagemaker-templates-service-catalog` module
- added `sagemaker-custom-kernel` module
- added batch inference project template to `sagemaker-templates-service-catalog` module
- added EFS removal policy to `mlflow-fargate` module
- added `mwaa` module with example dag which demonstrates the MLOps in Airflow
- added `sagemaker-model-event-bus` module.
- added `sagemaker-model-package-group` module.
- added `sagemaker-model-package-promote-pipeline` module.
- added `sagemaker-hugging-face-endpoint` module
- added `hf_import_models` template to import hugging face models
- added `qna-rag` module
- added `bedrock-finetuning` module

### **Changed**

- reogranized manifests by use-case
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
