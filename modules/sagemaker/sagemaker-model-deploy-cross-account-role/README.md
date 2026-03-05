# SageMaker Model Deploy Cross-Account Role

Creates an IAM role in a target account (pre-prod/prod) that allows a SageMaker model deployment pipeline in a source account (dev) to deploy endpoints cross-account.

## Features

- **Least Privilege**: Only grants permissions needed for SageMaker endpoint deployment
- **Explicit Trust**: Trusts only the specific pipeline role, not the entire source account
- **No CDK Bootstrap**: Independent of CDK bootstrap trust relationships

## Usage

Deploy this module once in each target account/region before deploying the model deployment pipeline.

### Example: Deploy to Pre-Prod Account

```yaml
name: preprod-deploy-role
path: git::https://github.com/awslabs/aiops-modules.git//modules/sagemaker/sagemaker-model-deploy-cross-account-role?ref=main
targetAccount: preprod
parameters:
  - name: trusted-account-id
    value: "111111111111"  # Dev account ID
  - name: trusted-role-name
    value: "model-deploy-pipeline-role"  # Pipeline role name
```

### Example: Deploy to Prod Account

```yaml
name: prod-deploy-role
path: git::https://github.com/awslabs/aiops-modules.git//modules/sagemaker/sagemaker-model-deploy-cross-account-role?ref=main
targetAccount: prod
parameters:
  - name: trusted-account-id
    value: "111111111111"  # Dev account ID
  - name: trusted-role-name
    value: "model-deploy-pipeline-role"  # Pipeline role name
```

## Deployment Order

1. Deploy this module to pre-prod account
2. Deploy this module to prod account
3. Deploy the model deployment pipeline in dev account
   - Pipeline will use the roles created by this module

## Permissions Granted

The role grants least-privilege permissions for:
- SageMaker endpoint/model/config CRUD operations
- IAM role management (for SageMaker execution roles)
- CloudFormation stack deployment
- S3 access to model artifacts
- ECR access to container images

## Outputs

- `DeployRoleArn`: ARN of the created deployment role

## Security

This module eliminates the need for wide-open CDK bootstrap trust relationships by creating explicit, scoped cross-account roles.
