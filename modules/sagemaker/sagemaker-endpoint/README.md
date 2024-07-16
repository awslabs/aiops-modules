# SageMaker Model Endpoint

## Description

This module creates SageMaker Model, Endpoint Configuration Production Variant, and a real-time Inference Endpoint. 
The endpoint is deployed in a VPC inside user-provided subnets.

The module supports provisioning of an endpoint from a model package, or may automatically pull
the latest approved model from model package group to support CI/CD deployment scenarios.

### Architecture

![SageMaker Endpoint Module Architecture](docs/_static/sagemaker-endpoint-module-architecture.png "SageMaker Endpoint Module Architecture")

## Inputs/Outputs

### Input Parameters

#### Required

- `vpc-id`: The VPC-ID that the endpoint will be created in.
- `subnet-ids`: The subnets that the endpoint will be created in.
- `model-package-arn`: Model package ARN `OR`
- `model-package-group-name`: Model package group name to pull latest approved model package from the group.

The user must specify either `model-package-arn` for a specific model or `model-package-group-name` to automatically
pull latest approved model from the model package group and deploy and endpoint. The latter is useful to scenarios
where endpoints are provisioned as part of automated Continuous Integration and Deployment pipeline.

#### Optional

- `sagemaker-project-id`: SageMaker project id
- `sagemaker-project-name`: SageMaker project name
- `sagemaker-domain-id`: SageMaker domain id
- `sagemaker-domain-arn`: SageMaker domain ARN. Used to tag resources with the `domain-arn`, which is used for domain resource isolation. If domain resource isolation is enabled `sagemaker-domain-arn` must be provided to ensure correct access to endpoint and other resources within the domain 
- `model-execution-role-arn`: Model execution role ARN. Will be created if not provided.
- `enable-network-isolation`: Enable network isolation on the model. `True` by default.
- `model-artifacts-bucket-arn`: Bucket ARN that contains model artifacts. Required by model execution IAM role to download model artifacts.
- `ecr-repo-arn`: ECR repository ARN if custom container is used
- `variant-name`: Endpoint config production variant name. `AllTraffic` by default.
- `initial-instance-count`: Initial instance count. `1` by default.
- `initial-variant-weight`: Initial variant weight. `1` by default.
- `instance-type`: instance type. `ml.m4.xlarge` by default.
- `managed-instance-scaling`: whether to enable managed instance autoscaling. `False` by default.
- `scaling-min-instance-count`: minimum autoscaling instance count. `1` by default. Only considered if `managed-instance-scaling` is `True`.
- `scaling-max-instance-count`: minimum autoscaling instance count. `10` by default. Only considered if `managed-instance-scaling` is `True`.
- `data-capture-samping-percentage`: the percentage of requests to capture data
- `data-capture-prefix`: the S3 prefix into `model-artifacts-bucket-arn` to store captured data

### Sample manifest declaration

```yaml
name: endpoint
path: modules/sagemaker/sagemaker-endpoint
parameters:
  - name: sagemaker_project_id
    value: dummy123
  - name: sagemaker_project_name
    value: dummy123
  - name: model_package_arn
    value: arn:aws:sagemaker:<region>:<account>:model-package/<package_name>/1
  - name: instance_type
    value: ml.m5.large
  - name: vpc_id
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking
        key: VpcId
  - name: subnet_ids
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking
        key: PrivateSubnetIds
  - name: sagemaker-domain-id
    valueFrom:
      moduleMetadata:
        group: sagemaker-studio
        name: studio
        key: StudioDomainId
  - name: sagemaker-domain-arn
    valueFrom:
      moduleMetadata:
        group: sagemaker-studio
        name: studio
        key: StudioDomainArn
```

### Module Metadata Outputs

- `ModelExecutionRoleArn`: SageMaker Model Execution IAM role ARN
- `ModelName`: SageMaker Model name
- `ModelPackageArn`: SageMaker Model package ARN
- `EndpointName`: SageMaker Endpoint name
- `EndpointUrl`: SageMaker Endpoint Url
- `KmsKeyId`: The KMS Key ID used for the SageMaker Endpoint assets bucket
- `SecurityGroupId`: The security group ID for the SageMaker Endpoint

#### Output Example

```json
{
  "ModelExecutionRoleArn": "arn:aws:iam::xxxxxxxxxxxx:role/xxxxxxxxxxxx",
  "ModelName": "mlops-mlops-sagemaker-endpoints-endpoint-model-xxxxxxxxxxxx",
  "EndpointName": "mlopsmlopssagemakerendpointsendpointendpoint-xxxxxxxxxxxx",
  "ModelPackageArn": "arn:aws:sagemaker:us-east-1:xxxxxxxxxxxx:model-package/model-mlops-demo/1",
  "EndpointUrl": "https://runtime.sagemaker.us-east-1.amazonaws.com/endpoints/mlopsmlopssagemakerendpointsendpointendpoint-xxxxxxxxxxxx/invocations",
  "KmsKeyId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "SecurityGroupId": "sg-xxxxxxxxxxxxxxxxx"
}
```
