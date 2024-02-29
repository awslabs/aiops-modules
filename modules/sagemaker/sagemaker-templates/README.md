# SageMaker Project Templates

This module creates organizational SageMaker Project Templates. 

The templates are registered in Service Catalog and available via SageMaker Studio Classic.

### Architecture

![SageMaker Templates Module Architecture](docs/_static/sagemaker-templates-module-architecture.png "SageMaker Templates Module Architecture")

## Inputs and outputs:
### Required inputs:
  - `portfolio-access-role-arn` - the ARN of the IAM Role used to access the Service Catalog Portfolio or SageMaker projects

### Optional Inputs:
  - `portfolio-name` - name of the Service Catalog Portfolio
  - `portfolio-owner` - owner of the Service Catalog Portfolio

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
