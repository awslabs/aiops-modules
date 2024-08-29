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

#### sample event for lambda function which will start the state machine
```json
{
  "config": {
    "bucket": "mlops-bucket",
    "prefix": "demo/scripts/input.yaml"
  }
}
```

### input to step function
Input to the state machine will be the json data generated from the yaml which is mentioned in input of lambda function as prefix.

Update the input.yaml as required. Refer https://docs.aws.amazon.com/step-functions/latest/dg/connect-sagemaker.html for supported inputs by step functions to connect to sagemaker.

#### sample input which is used to start the state machine.

```json
{
  "app_id": "aiops",
  "model_id": "demo",
  "job_prefix": "mlops",
  "preprocessing": {
    "run": true,
    "input": {
      "AppSpecification": {
        "ImageUri": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
        "ContainerEntrypoint": [
          "python3",
          "/opt/ml/processing/code/preprocessing.py"
        ]
      },
      "ProcessingResources": {
        "ClusterConfig": {
          "InstanceType": "ml.m5.xlarge",
          "InstanceCount": 1,
          "VolumeSizeInGB": 50
        }
      },
      "ProcessingInputs": [
        {
          "InputName": "input",
          "AppManaged": false,
          "S3Input": {
            "S3Uri": "s3://sagemaker-sample-data-us-east-1/processing/census",
            "LocalPath": "/opt/ml/processing/input",
            "S3DataType": "S3Prefix",
            "S3InputMode": "File",
            "S3DataDistributionType": "FullyReplicated"
          }
        },
        {
          "InputName": "Code",
          "AppManaged": false,
          "S3Input": {
            "S3Uri": "s3://mlops-bucket/demo/scripts",
            "LocalPath": "/opt/ml/processing/code",
            "S3DataType": "S3Prefix",
            "S3InputMode": "File",
            "S3DataDistributionType": "FullyReplicated"
          }
        }
      ],
      "ProcessingOutputConfig": {
        "Outputs": [
          {
            "OutputName": "train",
            "AppManaged": false,
            "S3Output": {
              "S3Uri": "s3://mlops-bucket/demo/processing/train",
              "LocalPath": "/opt/ml/processing/train",
              "S3UploadMode": "EndOfJob"
            }
          },
          {
            "OutputName": "test",
            "AppManaged": false,
            "S3Output": {
              "S3Uri": "s3://mlops-bucket/demo/processing/test",
              "LocalPath": "/opt/ml/processing/test",
              "S3UploadMode": "EndOfJob"
            }
          }
        ]
      },
      "StoppingCondition": {
        "MaxRuntimeInSeconds": 3600
      },
      "AppManaged": false,
      "Tags": [
        {
          "Key": "APP_ID",
          "Value": "aiops"
        }
      ],
      "Environment": null,
      "NetworkConfig": null,
      "RoleArn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole"
    }
  },
  "training": {
    "run": true,
    "input": {
      "AlgorithmSpecification": {
        "TrainingImage": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
        "ContainerEntrypoint": [
          "python3",
          "/opt/ml/input/data/code/train.py"
        ],
        "TrainingInputMode": "FastFile"
      },
      "HyperParameters": null,
      "ResourceConfig": {
        "InstanceType": "ml.m5.xlarge",
        "InstanceCount": 1,
        "VolumeSizeInGB": 50
      },
      "InputDataConfig": [
        {
          "ChannelName": "training",
          "DataSource": {
            "S3DataSource": {
              "S3DataType": "S3Prefix",
              "S3Uri": "s3://mlops-bucket/demo/processing/train",
              "S3DataDistributionType": "FullyReplicated"
            }
          }
        },
        {
          "ChannelName": "code",
          "DataSource": {
            "S3DataSource": {
              "S3DataType": "S3Prefix",
              "S3Uri": "s3://mlops-bucket/demo/scripts",
              "S3DataDistributionType": "FullyReplicated"
            }
          }
        }
      ],
      "OutputDataConfig": {
        "S3OutputPath": "s3://mlops-bucket/demo/model/"
      },
      "StoppingCondition": {
        "MaxRuntimeInSeconds": 3600
      },
      "Tags": [
        {
          "Key": "APP_ID",
          "Value": "aiops"
        }
      ],
      "Environment": null,
      "RetryStrategy": null,
      "VpcConfig": null,
      "RoleArn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole"
    }
  },
  "evaluation": {
    "run": true,
    "input": {
      "AppSpecification": {
        "ImageUri": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
        "ContainerEntrypoint": [
          "python3",
          "/opt/ml/processing/code/evaluation.py"
        ]
      },
      "ProcessingResources": {
        "ClusterConfig": {
          "InstanceType": "ml.m5.xlarge",
          "InstanceCount": 1,
          "VolumeSizeInGB": 50
        }
      },
      "ProcessingInputs": [
        {
          "InputName": "input",
          "AppManaged": false,
          "S3Input": {
            "S3Uri": "s3://mlops-bucket/demo/model/mlops-demo-1724940337/output/model.tar.gz",
            "LocalPath": "/opt/ml/processing/model",
            "S3DataType": "S3Prefix",
            "S3InputMode": "File",
            "S3DataDistributionType": "FullyReplicated"
          }
        },
        {
          "InputName": "Code",
          "AppManaged": false,
          "S3Input": {
            "S3Uri": "s3://mlops-bucket/demo/scripts",
            "LocalPath": "/opt/ml/processing/code",
            "S3DataType": "S3Prefix",
            "S3InputMode": "File",
            "S3DataDistributionType": "FullyReplicated"
          }
        },
        {
          "InputName": "test",
          "AppManaged": false,
          "S3Input": {
            "S3Uri": "s3://mlops-bucket/demo/processing/test",
            "LocalPath": "/opt/ml/processing/test",
            "S3DataType": "S3Prefix",
            "S3InputMode": "File",
            "S3DataDistributionType": "FullyReplicated"
          }
        }
      ],
      "ProcessingOutputConfig": {
        "Outputs": [
          {
            "OutputName": "evaluation",
            "AppManaged": false,
            "S3Output": {
              "S3Uri": "s3://mlops-bucket/demo/evaluation/output",
              "LocalPath": "/opt/ml/processing/evaluation",
              "S3UploadMode": "EndOfJob"
            }
          }
        ]
      },
      "StoppingCondition": {
        "MaxRuntimeInSeconds": 3600
      },
      "AppManaged": false,
      "Tags": [
        {
          "Key": "APP_ID",
          "Value": "aiops"
        }
      ],
      "Environment": null,
      "NetworkConfig": null,
      "RoleArn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole"
    }
  },
  "CreateModel": {
    "run": true,
    "input": {
      "EnableNetworkIsolation": null,
      "Containers": null,
      "VpcConfig": null,
      "PrimaryContainer": {
        "Image": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
        "ModelDataUrl": "s3://mlops-bucket/demo/model/mlops-demo-1724940337/output/model.tar.gz",
        "Environment": {
          "SAGEMAKER_PROGRAM": "inference.py",
          "SAGEMAKER_SUBMIT_DIRECTORY": "s3://mlops-bucket/demo/scripts/source.tar.gz"
        }
      },
      "ExecutionRoleArn": "arn:aws:iam::123456789012:role/SageMakerExecutionRole"
    }
  },
  "batchTransform": {
    "run": true,
    "input": {
      "BatchStrategy": "MultiRecord",
      "Environment": {
        "APP_ID": "aiops"
      },
      "MaxConcurrentTransforms": 2,
      "MaxPayloadInMB": 50,
      "TransformInput": {
        "ContentType": "text/csv",
        "SplitType": "Line",
        "DataSource": {
          "S3DataSource": {
            "S3DataType": "S3Prefix",
            "S3Uri": "s3://mlops-bucket/demo/processing/test/test_features.csv"
          }
        }
      },
      "TransformOutput": {
        "Accept": "text/csv",
        "AssembleWith": "Line",
        "S3OutputPath": "s3://mlops-bucket/demo/batch-output/mlops-demo-1724940337/"
      },
      "TransformResources": {
        "InstanceType": "ml.m5.xlarge",
        "InstanceCount": 1
      },
      "Tags": [
        {
          "Key": "APP_ID",
          "Value": "aiops"
        }
      ]
    }
  }
}
```



# Deployment Guide

See deployment steps in the [Deployment Guide](../../../DEPLOYMENT.md).


## Inputs/Outputs

### Input Parameters

#### Required

- `schedule`: cron expression to schedule the event to run the statemachine.

#### Optional

- `model-name` : Model Identifier  (default it is "demo")

## Sample manifest declaration

Create a manifest file under appropriate location, for example examples/manifests
```
name: mlops-stepfunctions
path: git::https://github.com/awslabs/aiops-modules.git//modules/examples/mlops-stepfunctions?ref=release/1.4.0&depth=1
parameters:
  - name: model-name
    value: demo
  - name: schedule
    value: "0 6 * * ? *"
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
