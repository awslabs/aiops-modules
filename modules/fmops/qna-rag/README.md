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

#### Optional

- `input-asset-bucket` - Input asset bucket that is used to store input documents

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
After deploying the Seedfarmer stack, Upload the file to be ingested into the input S3 bucket(If no input S3 bucket is provided in manifest, a bucket with name 'input-assets-bucket-dev-<AWSAccountNumber>' will be created by the construct)

The document summarization workflow can be invoked using GraphQL APIs. First invoke Subscription call followed by mutation call. 

The code below provides an example of a mutation call and associated subscription to trigger a pipeline call and get status notifications:

Subscription call to get notifications about the ingestion process:

```
subscription MySubscription {
  updateIngestionJobStatus(ingestionjobid: "123") {
    files {
      name
      status
      imageurl
    }
  }
}
_________________________________________________
Expected response:

{
  "data": {
    "updateIngestionJobStatus": {
      "files": [
        {
          "name": "a.pdf",
          "status": "succeed",
          "imageurl":"s3presignedurl"
        }
      ]
    }
  }
}
```
Where:
- ingestionjobid: id which can be used to filter subscriptions on client side
  The subscription will display the status and name for each file
- files.status: status update of the ingestion for the file specified
- files.name: name of the file stored in the input S3 bucket

Mutation call to trigger the ingestion process:

```
mutation MyMutation {
  ingestDocuments(ingestioninput: {
    embeddings_model: 
      {
        provider: Bedrock, 
        modelId: "amazon.titan-embed-text-v1",
        streaming: true
      }, 
    files: [{status: "", name: "a.pdf"}],
    ingestionjobid: "123",
    ignore_existing: true}) {
    files {
      imageurl
      status
    }
    ingestionjobid
  }
}
_________________________________________________
Expected response:

{
  "data": {
    "ingestDocuments": {
      "ingestionjobid": null
    }
  }
}
```
Where:
- files.status: this field will be used by the subscription to update the status of the ingestion for the file specified
- files.name: name of the file stored in the input S3 bucket
- ingestionjobid: id which can be used to filter subscriptions on client side
- embeddings_model: Based on type of modality (text or image ) the model provider , model id can be used.



After ingesting the input files , the QA process can be invoked using GraphQL APIs. First invoke Subscription call followed by mutation call.

The code below provides an example of a mutation call and associated subscription to trigger a question and get response notifications. The subscription call will wait for mutation requests to send the notifications.

Subscription call to get notifications about the question answering process:

```
subscription MySubscription {
  updateQAJobStatus(jobid: "123") {
    sources
    question
    answer
    jobstatus
  }
}
____________________________________________________________________
Expected response:

{
  "data": {
    "updateQAJobStatus": {
      "sources": [
        ""
      ],
      "question": "<base 64 encoded question>",
      "answer": "<base 64 encoded answer>",
      "jobstatus": "Succeed"
    }
  }
}
```

Where:

- jobid: id which can be used to filter subscriptions on client side
- answer: response to the question from the large language model as a base64 encoded string
- sources: sources from the knowledge base used as context to answer the question
- jobstatus: status update of the question answering process for the file specified

Mutation call to trigger the question:

```
mutation MyMutation {
  postQuestion(filename: "",
    embeddings_model: 
    {
      modality: "Text",
      modelId: "amazon.titan-embed-text-v1",
      provider: Bedrock,
      streaming: false
    },
    filename:"<file_name>"
    jobid: "123",
    jobstatus: "", 
    qa_model: 
      {
      provider: Bedrock,
      modality: "Text",
      modelId: "anthropic.claude-v2:1", 
      streaming: false,
      model_kwargs: "{\"temperature\":0.5,\"top_p\":0.9,\"max_tokens_to_sample\":250}"
    },
    question:"<base 64 encoded question>",
    responseGenerationMethod: RAG
    ,
    retrieval:{
      max_docs:10
    },
    verbose:false
  
  ) {
    jobid
    question
    verbose
    filename
    answer
    jobstatus
    responseGenerationMethod
  }
}
____________________________________________________________________
Expected response:

{
  "data": {
    "postQuestion": {
      "jobid": null,
      "question": null,
      "verbose": null,
      "filename": null,
      "answer": null,
      "jobstatus": null,
      "responseGenerationMethod": null
    }
  }
}
```

Where:

- jobid: id which can be used to filter subscriptions on client side
- jobstatus: this field will be used by the subscription to update the status of the question answering process for the file specified
- qa_model.modality/embeddings_model.modality: Applicable values Text or Image
- qa_model.modelId/embeddings_model.modelId: Model to process Q&A. example - anthropic.claude-v2:1,Claude-3-sonnet-20240229-v1:0
- retrieval.max_docs: maximum number of documents (chunks) retrieved from the knowledge base if the Retrieveal Augmented Generation (RAG) approach is used
- question: question to ask as a base64 encoded string
- verbose: boolean indicating if the [LangChain chain call verbosity](https://python.langchain.com/docs/guides/debugging#chain-verbosetrue) should be enabled or not
- streaming: boolean indicating if the streaming capability of Bedrock is used. If set to true, tokens will be send back to the subscriber as they are generated. If set to false, the entire response will be sent back to the subscriber once generated.
- filename: optional. Name of the file stored in the input S3 bucket, in txt format.
- responseGenerationMethod: optional. Method used to generate the response. Can be either RAG or LONG_CONTEXT. If not provided, the default value is LONG_CONTEXT.
