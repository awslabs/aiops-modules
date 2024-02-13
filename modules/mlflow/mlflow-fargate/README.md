# Mlflow on Fargate module

## Description

This module runs Mlflow on AWS Fargate.

## Inputs/Outputs

### Input Parameters

#### Required

- `vpc-id`: The VPC-ID that the ECS cluster will be created in.
- `subnet-ids`: The subnets that the Fargate task will use.
- `ecr-repository-name`: The name of the ECR repository to pull the image from.
- `artifacts-bucket-name`: Name of the artifacts store bucket

#### Optional

- `ecs-cluster-name`: Name of the ECS cluster.
- `service-name`: Name of the service.
- `task-cpu-units`: The number of cpu units used by the Fargate task.
- `task-memory-limit-mb`: The amount (in MiB) of memory used by the Fargate task.

### Sample manifest declaration

```yaml
name: mlflow-fargate
path: modules/mlflow/mlflow-fargate
parameters:
  - name: vpc-id
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking
        key: VpcId
  - name: subnet-ids
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking
        key: PrivateSubnetIds
  - name: ecr-repository-name
    valueFrom:
      moduleMetadata:
        group: storage
        name: ecr-mlflow
        key: EcrRepositoryName
  - name: artifacts-bucket-name
    valueFrom:
      moduleMetadata:
        group: storage
        name: buckets
        key: ArtifactsBucketName
```

### Module Metadata Outputs

- `ECSClusterName`: Name of the ECS cluster.
- `ServiceName`: Name of the service.
- `LoadBalancerDNSName`: Load balancer DNS name.

#### Output Example

```
{
  "ECSClusterName": "mlops-mlops-mlflow-mlflow-fargate-EcsCluster97242B84-xxxxxxxxxxxx",
  "ServiceName": "mlops-mlops-mlflow-mlflow-fargate-MlflowLBServiceEBACC043-xxxxxxxxxxxx",
  "LoadBalancerDNSName": "xxxxxxxxxxxx.elb.us-east-1.amazonaws.com"
}
```
