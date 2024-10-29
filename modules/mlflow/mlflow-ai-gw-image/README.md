# Mlflow AI Gateway Image

## Description

This module creates a [MLFlow AI Gateway](https://mlflow.org/docs/latest/llms/index.html#id2) server container image and pushes to the specified Elastic Container Repository.

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
        name: ecr-mlflow-ai-gw
        key: EcrRepositoryName
```

### Module Metadata Outputs

- `MlflowAIGWImageUri`: Mlflow AI Gateway image URI

#### Output Example

```json
{
  "MlflowAIGWImageUri": "xxxxxxxxxxxx.dkr.ecr.us-east-1.amazonaws.com/ecr-mlflow-ai-gw:latest"
}
```
