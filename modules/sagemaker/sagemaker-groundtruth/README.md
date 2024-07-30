## Introduction
This module provides an implementation for leveraging Amazon SageMaker Ground Truth for annotating images with missing labels using bounding boxes.


## Description

The module orchestrates the labeling process using an AWS Step Functions workflow. The high-level steps involved are:

- Retrieve a list of raw images from S3 and check Amazon SageMaker Feature Store for images with missing labels.
- Initiate a labeling job in SageMaker Ground Truth to label the remaining images.
- After the labeling job is completed, kick off a label verification job in SageMaker Ground Truth.
- Write the verified labels to the Feature Store.

Each of these steps is implemented using AWS Lambda functions. Simple wait/status check loops are used to monitor the status of the Ground Truth jobs.
## Architecture
![SageMaker Ground Truth Labelling Architecture](docs/_static/Sagemaker-groundtruth-module-Architecture.png "SageMaker Ground Truth Labelling Architecture")



## Deployment
The deployment of the required assets (Lambda functions, IAM roles, etc.) for the Step Functions workflow is automated using an AWS CDK app. The pipeline is triggered on a schedule as well as on Git commits, using two pipelines in AWS CodePipeline. The architecture of the CI/CD infrastructure deployed by the CDK app is as follows:


## Inputs/Outputs

### Input Parameters
#### Required
- Repository Details:

  - assets bucket: The name of S3 bucket with assets for the lambda functions and images for labelling.
  - repoName: The name of the repository where the source code is stored.
  - branchName: The branch name to use from the repository.

- Pipeline Configuration:

  - pipelineAssetsPrefix: The S3 prefix where the pipeline assets will be stored.
  
- SageMaker Configuration:

  - featureGroupName: The name of the Feature Group in SageMaker Feature Store where the labels will be stored.

The s3 bucket is created as part of an init stack. This bucket name is used as input.

Additionally, there are 2 configuration files to provide inputs

[config](config.yaml)
- Contains the configuration settings for the labeling pipeline, such as the CodeCommit repository, branch, S3 prefix, labeling job settings, workteam ARNs, and SageMaker Feature Store and Model Registry details

[repo config](repo_config.yaml)
- Defines the git repositroy to use, options:
    - "CODECOMMIT" - will create a new codecommit repo with name specified in repoName
    - "GITHUB" - will use an existing codestar connection for GitHub source


#### Optional
- Pipeline Configuration:
  - labelingJobPrivateWorkteamArn: The ARN of the private work team for labeling jobs (if usePrivateWorkteamForLabeling is true).
  - usePrivateWorkteamForLabeling: A boolean flag indicating whether to use a private work team for labeling jobs.
  - usePrivateWorkteamForVerification: A boolean flag indicating whether to use a private work team for verification jobs.
  - verificationJobPrivateWorkteamArn: The ARN of the private work team for verification jobs (if usePrivateWorkteamForVerification is true).
  - maxLabelsPerLabelingJob: The maximum number of labels per labeling job.
  - labelingPipelineSchedule: The schedule for triggering the labeling pipeline (e.g., a cron expression).

- SageMaker Configuration:

  - featureGroupName: The name of the Feature Group in SageMaker Feature Store where the labels will be stored.
  - modelPackageGroupName: The name of the Model Package Group in SageMaker Model Registry.
  - modelPackageGroupDescription: The description of the Model Package Group in SageMaker Model Registry.


#### Input Example
- aiopsdatabucket: "aiops-init-stack-labelingdatabucketXX12345"
- featureGroupName: "tag-quality-inspection"
- repoName: "aiops-to-greengrass-cs"

### Module Metadata Outputs
labelingPipelineArn: The ARN of the Step Functions state machine for the labeling pipeline.
labelingPipelineName: The name of the Step Functions state machine for the labeling pipeline.


#### Output Example
```
{
  "labelingPipelineArn": "arn:aws:states:us-east-1:123456789012:stateMachine:MyLabelingPipeline",
  "LabelingPipelineNameExport": "aiopsEdge-Labeling-Pipeline"
}
```