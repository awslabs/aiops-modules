# Introduction

## Description

This module runs a demo [Strands](https://strandsagents.com/latest/) Weather Agent on [Amazon EKS Auto Mode](https://aws.amazon.com/eks/auto-mode/).

The module will:
1. Provision an Amazon EKS Auto Mode Cluster
2. Build Weather Agent Docker image and push into Amazon ECR repository
3. Create and associate Amazon EKS service account permissions to an IAM Role with Amazon Bedrock access
4. Deploy Weather Agent to Amazon EKS using a Helm chart

### Required Parameters

- `eks-cluster-name`: Amazon EKS Cluster name
- `ecr-repo-name`: Amazon ECR Repository name

### Sample manifest declaration

```yaml
name: weather-agent
path: modules/agents/eks-strands-agents-demo
parameters:
  - name: EksClusterName
    value: eks-strands-agents-demo
```