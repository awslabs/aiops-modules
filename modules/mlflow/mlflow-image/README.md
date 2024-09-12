# Mlflow Image

## Description

This module creates an mlflow tracking server container image and pushes to the specified Elastic Container Repository.

## Inputs/Outputs

### Input Parameters

#### Required

- `ecr-repository-name`: The name of the ECR repository to push the image to.

### Sample manifest declaration

```yaml
name: mlflow-image
path: modules/mlflow/mlflow-image
parameters:
  - name: ecr-repository-name
    valueFrom:
      moduleMetadata:
        group: storage
        name: ecr-mlflow
        key: EcrRepositoryName
```

### Module Metadata Outputs

- `MlflowImageUri`: Mlflow image URI

#### Output Example

```json
{
  "MlflowImageUri": "xxxxxxxxxxxx.dkr.ecr.us-east-1.amazonaws.com/ecr-mlflow:latest"
}
```
