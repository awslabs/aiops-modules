## Introduction
Machine Learning Operations (MLOps) is the practice of operationalizing the end-to-end machine learning workflow, from data preparation to model deployment and monitoring. AWS Step Functions, combined with AWS SageMaker, provides a powerful solution for building and orchestrating MLOps pipelines.

AWS Step Functions is a serverless function orchestrator that allows you to coordinate multiple AWS services into flexible, resilient, and highly available workflows. It acts as the glue that ties together various components of your MLOps pipeline, ensuring that tasks are executed in the correct order and with the required dependencies.

AWS SageMaker, on the other hand, is a fully managed machine learning service that provides tools and resources for building, training, and deploying machine learning models. It simplifies the complexities of managing infrastructure and libraries for your machine learning workloads.


## Description

This module shows how to integrate the AWS Step Functions with SageMaker, to create robust and scalable MLOps pipelines that automate the entire machine learning lifecycle.

Here's a typical workflow:

1. Data Preprocessing: Using AWS SageMaker Processing, you can preprocess your data by performing tasks such as data cleaning, feature engineering, and data splitting.

2. Model Training: Leverage SageMaker's built-in algorithms or bring your own custom code to train your machine learning model on the preprocessed data.

3. Model Evaluation: Evaluate the trained model's performance using metrics like accuracy, precision, recall, or custom metrics specific to your use case.

4. Model Approval: Implement manual or automated approval steps to review the model's performance and decide whether to proceed with deployment.

5. Model Deployment: Deploy your trained model to a SageMaker endpoint, making it available for real-time inference or batch processing.



# Deployment Guide

## Set-up the environment(s)

1. Clone the repository and checkout a release branch using the below command:

```
git clone --origin upstream --branch release/1.4.0 https://github.com/awslabs/aiops-modules
```
The release version can be replaced with the version of interest.

2. Move into the `aiops-modules` repository:
```
cd aiops-modules
```
3. Create and activate a Virtual environment
```
python3 -m venv .venv && source .venv/bin/activate
```
4. Install the requirements
```
pip install -r ./requirements.txt
```
5. Set environment variables

Replace the values below with your AWS account id and Administrator IAM Role.
```
export PRIMARY_ACCOUNT=XXXXXXXXXXXX
export ADMIN_ROLE_ARN=arn:aws:iam::XXXXXXXXXXXX:role/XXXXX
```

5. Bootstrap the CDK environment (one time per region) with CDK V2. Assuming you are deploying in `us-east-1`:
```
cdk bootstrap aws://${PRIMARY_ACCOUNT}/us-east-1
```
6. Bootstrap AWS Account(s)

Assuming that you will be using a single account, follow the guide [here](https://seed-farmer.readthedocs.io/en/latest/bootstrapping.html#) to bootstrap your account(s) to function as a toolchain and target account.

Following is the command to bootstrap your existing account to a toolchain and target account.
```
seedfarmer bootstrap toolchain --project aiops --trusted-principal ${ADMIN_ROLE_ARN} --as-target
```

## Deployment

Pick the manifest to deploy. Manifests are located in `manifests/` directory. For example, to deploy this modules, run:

!Note: if you are deploying into a region different from `us-east-1`, change the `regionMappings` in `deployment.yaml`.
```
seedfarmer apply manifests/mlops-stepfunctions/deployment.yaml
```