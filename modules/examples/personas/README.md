# Personas Module

## Description

This module deploys various roles required for an AI/ML project, including:

- Data Engineer
- ML Engineer
- MLOps
- IT Auditor
- Model Auditor

The module creates separate roles with appropriate permissions and policies for each persona, ensuring proper segregation of duties and access control within the AI/ML project.

## Inputs/Outputs

### Input Parameters

#### Required

- `project_name`: The name of the AI/ML project for which the roles are being created.
- `environment`: The environment for which the roles are being created (e.g., dev, staging, prod).

#### Optional

- `additional_policies`: A list of additional IAM policies to attach to the roles (e.g., for accessing specific AWS services or resources).

### Module Outputs

- `data_engineer_role_arn`: The ARN of the Data Engineer role.
- `ml_engineer_role_arn`: The ARN of the ML Engineer role.
- `mlops_role_arn`: The ARN of the MLOps role.
- `it_auditor_role_arn`: The ARN of the IT Auditor role.
- `model_auditor_role_arn`: The ARN of the Model Auditor role.

## Usage

To deploy an uber-manifest containing all modules, run:

Note: this is an uber-manifest that contains other modules also. It may take a while to deploy.
```
seedfarmer apply examples/manifests/deployment.yaml
```