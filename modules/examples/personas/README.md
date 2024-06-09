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

To use this module, include it in your CDK application and provide the required input parameters. For example:

```python
from aws_cdk import App, Stack
from personas_module import PersonasModule

app = App()
stack = Stack(app, "PersonasStack", env={"region": "us-west-2"})

personas_module = PersonasModule(stack, "PersonasModule",
    project_name="my-ai-ml-project",
    environment="dev",
    additional_policies=[
        "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess",
        "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
    ]
)

app.synth()