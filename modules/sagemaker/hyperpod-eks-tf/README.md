# Amazon SageMaker Hyperpod Cluster Module

## Description

This module creates the below AWS resources:

- Networking: VPC, Subnets, Security Groups, NAT Gateway
- Amazon SageMaker HyperPod clusters orchestrated by Amazon EK
- Amazon S3 Buckets & IAM Roles

## Inputs/Outputs

### Input Paramenters

#### Required

- `HyperpodClusterName`: Cluster name
- `AvailabilityZoneId`: AZ id e.g. `use1-az1` or `usw2-az1`. WARNING: must match your training plan availablity zone
- `AccelInstanceType`: EC2 imstance type e.g. `ml.p5en.48xlarge`
- `AccelCount`: Number of instances
- `AccelVolumeSize`: Disk volume size
- `TrainingPlanArn`: Arn of the training plan
- `NodeRecovery`: Set to `None` to disable; `Automatic` by default
- `ArtifactsBucketName`: An S3 bucket name (data bucket)
- `TfstateBucketName`: An S3 bucket name (terraform state bucket)

Due to lack of terraform awscc provider and AWS CDK support for `TrainingPlanArn` property when creating SageMaker HyperPod clusters, temporarily if `TrainingPlanArn` is provided, a cluster will be created using API and not IaC. If not using `TrainingPlanArn`, a default cluster is created with a default instance group. Please note you are required to install helm charts on the cluster yourself if using training plans.