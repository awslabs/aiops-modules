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

See deployment steps in the [Deployment Guide](../../../DEPLOYMENT.md).


## Inputs/Outputs

### Input Parameters

#### Required

- `model-name` : Model Identifier  (default it is "demo")
- `hours`: Time in UTC hour to schedule the event to run the statemachine daily.

## Sample manifest declaration

Create a manifest file under appropriate location, for example examples/manifests
```
name: mlops-stepfunctions
path: git::https://github.com/awslabs/aiops-modules.git//modules/examples/mlops-stepfunctions?ref=release/1.4.0&depth=1
parameters:
  - name: model-name
    value: demo
  - name: hours
    value: "18"
```

### Module Metadata Outputs

- `MlOpsBucket`: Name of the Bucket where Model Artifacts are stored.
- `SageMakerExecutionRole`: Execution Roles used by SageMaker Service.
- `ImageUri`: Docker Image URI used by SageMaker Jobs.
- `StateMachine`: ARN of State Machine.
- `LambdaFunction`: ARN of Lambda function which starts the execution of State Machine.

#### Output Example

```yaml
metadata: | {
    "MlOpsBucket": "",
    "SageMakerExecutionRole": "arn:aws:iam::123456789012:role/SageMakerExecutionRole",
    "ImageUri": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
    "StateMachine": "arn:aws:states:us-east-1:123456789012:stateMachine:MLOpsStateMachine",
    "LambdaFunction": "arn:aws:lambda:us-east-1:123456789012:function:MlOpsLambdaFunction",
}
```