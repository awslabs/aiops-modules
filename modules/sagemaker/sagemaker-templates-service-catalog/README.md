# SageMaker Project Templates

This module creates organizational SageMaker Project Templates. 

The templates are registered in Service Catalog and available via SageMaker Studio Classic.

### Architecture

![SageMaker Templates via Service Catalog Module Architecture](docs/_static/sagemaker-templates-service-catalog-module-architecture.png "SageMaker Templates in Service Catalog Module Architecture")

### Project Templates

The module contains ogranizational SageMaker Project Templates vended as Service Catalog Products. Using the templates is available through SageMaker Studio Classic and AWS Service Catalog.

#### Basic Multi-Account Template

This project template contains basic multi-account template from [AWS Enterprise MLOps Framework](https://github.com/aws-samples/aws-enterprise-mlops-framework/blob/main/mlops-multi-account-cdk/mlops-sm-project-template/README.md#sagemaker-project-stack).
The template contains SageMaker Pipeline to train a model on Abalone dataset using XGBoost, perform evaluation, and an example CI/CD pipeline to deploy the model endpoints to multiple AWS accounts.

![Basic Multi-Account Template](https://github.com/aws-samples/aws-enterprise-mlops-framework/blob/main/mlops-multi-account-cdk/mlops-sm-project-template/diagrams/mlops-sm-project-general-architecture.jpg)

#### Batch Inference Template

This project template contains SageMaker pipeline that performs batch inference.

![Batch Inference Template](docs/_static/batch-inference-template.png "Batch Inference Template Architecture")

## Inputs and outputs:
### Required inputs:
  - `portfolio-access-role-arn` - the ARN of the IAM Role used to access the Service Catalog Portfolio or SageMaker projects

### Optional Inputs:
  - `portfolio-name` - name of the Service Catalog Portfolio
  - `portfolio-owner` - owner of the Service Catalog Portfolio
  - `dev-vpc-id` - id of VPC in dev environment
  - `dev-subnet-ids` - list of subnet ids
  - `dev-security-group-ids` - list of security group ids
  - `pre-prod-account-id` - pre-prod account id
  - `pre-prod-region` - pre-prod region
  - `pre-prod-vpc-id` - id of VPC in pre-prod environment
  - `pre-prod-subnet-ids` - list of subnet ids
  - `pre-prod-security-group-ids` - list of security group ids
  - `prod-account-id` - prod account id
  - `prod-region` - prod region
  - `prod-vpc-id` - id of VPC in prod environment
  - `prod-subnet-ids` - list of subnet ids
  - `prod-security-group-ids` - list of security group ids

### Sample manifest declaration

```yaml
name: templates
path: modules/sagemaker/sagemaker-templates
targetAccount: primary
parameters:
  - name: portfolio-access-role-arn
    valueFrom:
      moduleMetadata:
        group: sagemaker-studio
        name: studio
        key: LeadDataScientistRoleArn
```

### Outputs (module metadata):
  - `ServiceCatalogPortfolioName` - the name of the Service Catalog Portfolio
  - `ServiceCatalogPortfolioOwner` - the owner of the Service Catalog Portfolio

### Example Output:
```yaml
{
  "ServiceCatalogPortfolioName": "MLOps SageMaker Project Templates",
  "ServiceCatalogPortfolioOwner": "administrator"
}
```
