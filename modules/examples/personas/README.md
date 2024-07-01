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

## Sample manifest declaration
Create a manifest file under appropriate location, for example examples/manifests
```
name: personas
path: modules/examples/personas
```
### Outputs (module metadata):
  - `MLEngineerRoleArn` - the arn of the Machine Learning Engineer Role
  - `DataEngineerRoleArn` - the arn of the Data Engineer Role
  - `ITLeadRoleArn` - the arn of the Machine IT Lead Role
  - `BusinessAnalystRoleArn` - the arn of the Business Analyst Role
  - `MLOpsEngineerRoleArn` - the arn of the Machine Learning Ops Engineer Role
  - `ITAuditorRoleArn` - the arn of the IT Auditor Role
  - `ModelRiskManagerRoleArn` - the arn of the Model Risk Manager Role

### Example Output:
```yaml
metadata: |
  {
    "MLEngineerRoleArn": "arn:aws:iam::<account_id>:role/MyStack-MLEngineerRole-<random_string>",
    "DataEngineerRoleArn": "arn:aws:iam::<account_id>:role/MyStack-DataEngineerRole-<random_string>",
    "ITLeadRoleArn": "arn:aws:iam::<account_id>:role/MyStack-ITLeadRole-<random_string>",
    "BusinessAnalystRoleArn": "arn:aws:iam::<account_id>:role/MyStack-BusinessAnalystRole-<random_string>",
    "MLOpsEngineerRoleArn": "arn:aws:iam::<account_id>:role/MyStack-MLOpsEngineerRole-<random_string>",
    "ITAuditorRoleArn": "arn:aws:iam::<account_id>:role/MyStack-ITAuditorRole-<random_string>",
    "ModelRiskManagerRoleArn": "arn:aws:iam::<account_id>:role/MyStack-ModelRiskManagerRole-<random_string>"
  }
```