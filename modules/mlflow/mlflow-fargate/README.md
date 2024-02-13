# Mlflow on Fargate module

## Description

This module runs Mlflow on Fargate.

## Inputs/Outputs

### Input Parameters

#### Required

- `vpc-id`: The VPC-ID that the cluster will be created in.
- `subnet-ids`: The subnets that the cluster will be created in.
- `ecr-repository-name`: The name of the ECR repository to pull the image from.
- `artifacts-bucket-name`: Name of the artifacts store bucket

#### Optional

- `ecs-cluster-name`: Name of the ECS cluster
- `service-name`: name of the service