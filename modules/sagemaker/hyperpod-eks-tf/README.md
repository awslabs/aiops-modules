# Amazon SageMaker Hyperpod Cluster Module

## Description

This module creates the below AWS resources:

- Networking: VPC, Subnets, Security Groups, NAT Gateway
- Amazon SageMaker HyperPod clusters orchestrated by Amazon EK
- Amazon S3 Buckets & IAM Roles

## Inputs/Outputs

### Input Paramenters

#### Required

- `AvailabilityZoneId`: AZ id e.g. `use1-az1` or `usw2-az1`. WARNING: must match your training plan availablity zone
- `ArtifactsBucketName`: An S3 bucket name (data bucket)
- `TfstateBucketName`: An S3 bucket name (terraform state bucket)
