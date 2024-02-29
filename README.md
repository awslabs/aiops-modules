# MLOps Modules

MLOps modules is a collection of resuable Infrastructure as Code (IAC) modules that works with [SeedFarmer CLI](https://github.com/awslabs/seed-farmer). Please see the [DOCS](https://seed-farmer.readthedocs.io/en/latest/) for all things seed-farmer.

The modules in this repository are decoupled from each other and can be aggregated together using GitOps (manifest file) principles provided by `seedfarmer` and achieve the desired use cases. It removes the undifferentiated heavy lifting for an end user by providing hardended modules and enables them to focus on building business on top of them.

## General Information

The modules in this repository are / must be generic for reuse without affiliation to any one particular project in Machine Learning Operations domain.

All modules in this repository adhere to the module structure defined in the the [SeedFarmer Guide](https://seed-farmer.readthedocs.io/en/latest)

- [Project Structure](https://seed-farmer.readthedocs.io/en/latest/project_development.html)
- [Module Development](https://seed-farmer.readthedocs.io/en/latest/module_development.html)
- [Module Manifest Guide](https://seed-farmer.readthedocs.io/en/latest/manifests.html)

## Modules

### SageMaker Modules

| Type                                                                                     | Description                                                                                                                                                                    |
|------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [SageMaker Endpoint Module](modules/sagemaker/sagemaker-endpoint/README.md)              | Creates SageMaker real-time inference endpoint for the specified model package or latest approved model from the model package group                                           |
| [SageMaker Studio Module](modules/sagemaker/sagemaker-studio/README.md)                  | Provisions secure SageMaker Studio Domain environment, creates example User Profiles for Data Scientist and Lead Data Scientist linked to IAM Roles, and adds lifecycle config |
| [SageMaker Notebook Instance Module](modules/sagemaker/sagemaker-notebook/README.md)     | Creates SageMaker Notebook Instances                                                                                                                                           |

### Mlflow Modules

| Type                                                                    | Description                                                                                                                                                                                       |
|-------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [Mlflow Image Module](modules/mlflow/mlflow-image/README.md)            | Creates Mlflow Docker container image and pushes the image to Elastic Container Registry                                                                                                          |
| [Mlflow on AWS Fargate Module](modules/mlflow/mlflow-fargate/README.md) | Runs Mlflow container on AWS Fargate in a load-balanced Elastic Container Service. Supports Elastic File System and Relational Database Store for metadata persistence, and S3 for artifact store |

### FMOps Modules

| Type                                                                                                            | Description                                                     |
|-----------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| [SageMaker JumpStart Foundation Model Endpoint Module](modules/fmops/sagemaker-jumpstart-fm-endpoint/README.md) | Creates an endpoint for a SageMaker JumpStart Foundation Model. |

### Industry Data Framework (IDF) Modules

The modules in this repository are compatible with [Industry Data Framework (IDF) Modules](https://github.com/awslabs/idf-modules) and can be used together within the same deployment. Refer to `examples/manifests` for examples.
