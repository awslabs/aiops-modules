# SageMaker Project Templates

This module creates organizational SageMaker Project Templates. 

The templates are registered in Service Catalog and available via SageMaker Studio Classic.

### Architecture

![SageMaker Templates via Service Catalog Module Architecture](docs/_static/sagemaker-templates-service-catalog-module-architecture.png "SageMaker Templates in Service Catalog Module Architecture")

### Project Templates

The module contains ogranizational SageMaker Project Templates vended as Service Catalog Products. Using the templates is available through SageMaker Studio Classic and AWS Service Catalog.

#### Train a model on Abalone dataset with XGBoost Template

The template contains an example SageMaker Pipeline to train a model on Abalone dataset using XGBoost, and perform model evaluation.

![Abalone with XGBoost](docs/_static/abalone-xgboost-template.png "Abalone with XGBoost Template Architecture")

#### LLM fine-tuning and evaluation

The template is based on LLM fine-tuning template from [AWS Enterprise MLOps Framework](https://github.com/aws-samples/aws-enterprise-mlops-framework/tree/main/mlops-multi-account-cdk/mlops-sm-project-template/mlops_sm_project_template/templates/finetune_deploy_llm_product).

![LLM fine-tuning and evaluation template](docs/_static/llm-evaluate.png "LLM Evaluate Template Architecture")
![SM pipeline graph](docs/_static/llm-evaluation-pipeline-graph.png "SM Pipeline graph")

The template is based on basic multi-account template from [AWS Enterprise MLOps Framework](https://github.com/aws-samples/aws-enterprise-mlops-framework/blob/main/mlops-multi-account-cdk/mlops-sm-project-template/README.md#sagemaker-project-stack).

#### Batch Inference Template

This project template contains SageMaker pipeline that performs batch inference.

![Batch Inference Template](docs/_static/batch-inference-template.png "Batch Inference Template Architecture")

#### Huggingface Model Import Template

This project template contains SageMaker pipeline that imports a hugging face model based on model id and access 
token inputs.

![Huggingface model import template](docs/_static/huggingface-model-import.png "Hugging Face Model Import Template 
Architecture")

#### Multi-account Model Deployment Template

The template contains an example CI/CD pipeline to deploy the model endpoints to multiple AWS accounts. 

![Multi-account Model Deployment](docs/_static/multi-account-model-deploy-template.png "Multi-account Model Deployment Template Architecture")

The template is based on basic multi-account template from [AWS Enterprise MLOps Framework](https://github.com/aws-samples/aws-enterprise-mlops-framework/blob/main/mlops-multi-account-cdk/mlops-sm-project-template/README.md#sagemaker-project-stack).

#### Third-party Code Repository Integration 
SageMaker templates support third party code repository (GitHub) integration along with default AWS CodeCommit. As part of integration, SageMaker templates will be able to manage (create, delete) repositories. As an example, if `sagemaker-templates-service-catalog` template configured to use GitHub as repository type then it would create code repository directly into GitHub account provided with manifest configuration. Repository will be named after SageMaker project name in AWS account `{sagemaker-project}-deploy`. For example, if SageMaker project name is `aiops-abalone-model` then GitHub repository would be created with name `aiops-abalone-model-deploy`.


## Prerequesites:
### AWS CodeCommit repository integration
- There isn't any prerequesite for using CodeCommit repository with SageMaker templates. It is supported as default repository.
> [!IMPORTANT] 
> It is important to note AWS CodeCommit is no longer available to new customers. Existing customers of AWS CodeCommit can continue to use the service as normal. 
### GitHub repository integration
- Target AWS account should contain AWS Secret Manager secret that contains GitHub personal access token with required permissions to manage repository. Refer guide [Creating a fine-grained personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token) in order to create access token.
- Template also requires AWS CodeConnection created for GitHub provider in order to integrated GitHub repositories AWS CodeBuild and AWS CodePipeline. Refer guide [Create a connection to GitHub](https://docs.aws.amazon.com/dtconsole/latest/userguide/connections-create-github.html) in order to create connection with GitHub.

## Inputs and outputs:
### Required inputs:
  - `portfolio-access-role-arn` - the ARN of the IAM Role used to access the Service Catalog Portfolio or SageMaker projects
### Optional Inputs:
  - `repository-type` - type of repository to be integrated with Sagemaker template source code, exp. `GitHub`. If `CodeCommit` is provided then other GitHub repository params are ignored. This is optional parameter, if not provided `CodeCommit` is set as default
  - `repository-owner` - owner or organisation of project code repository 
  - `access-token-secret-name` - AWS Secret Manager secret name where access token is stored, this is used to manage repository from template
  - `aws-codeconnection-arn` -  AWS CodeConnection ARN for repository provider, currently template supports GitHub provider
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
  - `sagemaker-domain-id`: SageMaker domain id
  - `sagemaker-domain-arn`: SageMaker domain ARN. Used to tag resources with the `domain-arn`, which is used for domain resource isolation. If domain resource isolation is enabled `sagemaker-domain-arn` must be provided to ensure correct access to resources within the domain

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
  # Below are the optional properties passed to the multi-account CI/CD deployment template
  - name: dev-account-id
    valueFrom:
      envVariable: PRIMARY_ACCOUNT
  - name: dev-region
    valueFrom:
      envVariable: PRIMARY_REGION
  - name: dev-vpc-id
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking
        key: VpcId
  - name: dev-subnet-ids
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking
        key: PrivateSubnetIds
  - name: pre-prod-account-id
    valueFrom:
      envVariable: PRE_PROD_ACCOUNT
  - name: pre-prod-region
    valueFrom:
      envVariable: PRE_PROD_REGION
  - name: pre-prod-vpc-id
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking-pre-prod
        key: VpcId
  - name: pre-prod-subnet-ids
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking-pre-prod
        key: PrivateSubnetIds
  - name: prod-account-id
    valueFrom:
      envVariable: PROD_ACCOUNT
  - name: prod-region
    valueFrom:
      envVariable: PROD_REGION
  - name: prod-vpc-id
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking-prod
        key: VpcId
  - name: prod-subnet-ids
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking-prod
        key: PrivateSubnetIds
  - name: sagemaker-domain-id
    valueFrom:
      moduleMetadata:
        group: sagemaker-studio
        name: studio
        key: StudioDomainId
  - name: sagemaker-domain-arn
    valueFrom:
      moduleMetadata:
        group: sagemaker-studio
        name: studio
        key: StudioDomainArn
```
### Sample manifest example for source repository options
[sagemaker-templates-modules-github.yaml](/examples/manifests/sagemaker-templates-modules-github.yaml)
[sagemaker-templates-modules-codecommit.yaml](/examples/manifests/sagemaker-templates-modules-codecommit.yaml)

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
