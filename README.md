# MLOps Modules

MLOps modules is a collection of resuable Infrastructure as Code (IAC) modules that works with [SeedFarmer CLI](https://github.com/awslabs/seed-farmer). Please see the [DOCS](https://seed-farmer.readthedocs.io/en/latest/) for all things seed-farmer.

The modules in this repository are decoupled from each other and can be aggregated together using GitOps (manifest file) principles provided by `seedfarmer` and achieve the desired use cases. It removes the undifferentiated heavy lifting for an end user by providing hardended modules and enables them to focus on building business on top of them.

## General Information

The modules in this repository are / must be generic for reuse without affiliation to any one particular project in Machine Learning Operations domain.

All modules in this repository adhere to the module strutucture defined in the the [SeedFarmer Guide](https://seed-farmer.readthedocs.io/en/latest)

- [Project Structure](https://seed-farmer.readthedocs.io/en/latest/project_development.html)
- [Module Development](https://seed-farmer.readthedocs.io/en/latest/module_development.html)
- [Module Manifest Guide](https://seed-farmer.readthedocs.io/en/latest/manifests.html)

## Modules

### SageMaker Modules

| Type                                                                        | Description                                     |
|-----------------------------------------------------------------------------|-------------------------------------------------|
| [SageMaker Endpoint Module](modules/sagemaker/sagemaker-endpoint/README.md) | Creates SageMaker real-time inference endpoint. |
| [SageMaker Studio Module](modules/sagemaker/sagemaker-studio/README.md)     | Creates SageMaker Studio Domain.                |


### Industry Data Framework (IDF) Modules

The modules in this repository are compatible with [Industry Data Framework (IDF) Modules](https://github.com/awslabs/idf-modules) and can be used together within the same deployment. Refer to `examples/manifests` for examples.
