# Personas Module

## Description

This module is an example that deploys various roles that may be required for an AI/ML project, including:

- ML Engineer
- Data Engineer
- IT Lead
- Business Analyst
- MLOPs Engineer
- IT Auditor
- Model Risk Manager

The module creates separate roles with appropriate permissions and policies for each persona, ensuring proper segregation of duties and access control within the AI/ML project.

## Inputs/Outputs

### Input Parameters

#### Optional

- `bucket_name`: S3 bucket name to add permissions for

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