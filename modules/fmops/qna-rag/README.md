# AppSync endpoint for Question and Answering using RAG

## Description

Deploys an AWS AppSync endpoint for ingestion of data and use it as knowledge base for a Question and Answering model using RAG 

The module uses [AWS Generative AI CDK Constructs](https://github.com/awslabs/generative-ai-cdk-constructs/tree/main).

### Architecture
Knowledge Base Ingestion Architecture
![AWS Appsync Ingestion Endpoint Module Architecture](docs/_static/ingestion_architecture.png "AWS Appsync Ingestion Endpoint Module Architecture")

Question and Answering using RAG Architecture
![AWS Appsync Question and Answering Endpoint Module Architecture](docs/_static/architecture.png "AWS Appsync Question and Answering RAG module Endpoint Module Architecture")

## Inputs/Outputs

### Input Parameters

#### Required

- `cognito-pool-id` - ID of the cognito user pool, used to secure GraphQl API
- `os-domain-endpoint` - Open Search doamin url used as knowledge base
- `os-security-group-id` - Security group of open search cluster
- `vpc-id` - VPC id

### Module Metadata Outputs

- `IngestionGraphqlApiId` - Ingestion Graphql API ID.
- `IngestionGraphqlArn` - Ingestion Graphql API ARN.
- `QnAGraphqlApiId` - Graphql API ID.
- `QnAGraphqlArn` - Graphql API ARN.
- `InputAssetBucket` - Input S3 bucket.
- `ProcessedInputBucket` - S3 bucket for storing processed output.

## Examples

Example manifest:

```yaml
name: qna-rag
path: modules/fmops/qna-rag
parameters:
  - name: cognito-pool-id
    #Replace below value with valid congnito pool id
    value: us-east-1_XXXXX
  - name: os-domain-endpoint
    valueFrom:
      moduleMetadata:
        group: storage
        name: opensearch
        key: OpenSearchDomainEndpoint
  - name: os-security-group-id
    valueFrom:
      moduleMetadata:
        group: storage
        name: opensearch
        key: OpenSearchSecurityGroupId
  - name: vpc-id
    valueFrom:
      moduleMetadata:
        group: networking
        name: networking
        key: VpcId

```
