# Ray Cluster

## Description

This module creates a Ray cluster in AWS EKS Kubernetes cluster. It deploys a RayClsuter via [kuberay-helm](https://github.com/ray-project/kuberay-helm) and a ClusterIP service.

## Inputs/Outputs

### Input Parameters

#### Required

- `eks_cluster_name` - Name of the EKS cluster to deploy to
- `eks_cluster_admin_role_arn`- ARN of EKS admin role to authenticate kubectl
- `eks_oidc_arn` - ARN of EKS OIDC provider for IAM roles
- `namespace` - Kubernetes namespace name
- `service_account_name` - Service account name

#### Optional

- `tags` - List of additional tags to apply to all resources

### Sample manifest declaration

```yaml
name: ray-cluster
path: modules/eks/ray-cluster
parameters:
  - name: EksClusterAdminRoleArn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterMasterRoleArn
  - name: EksClusterName
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterName
  - name: EksClusterEndpoint
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterEndpoint
  - name: EksOidcArn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksOidcArn
  - name: Namespace
    valueFrom:
      parameterValue: rayNamespaceName
  - name: ServiceAccountName
    valueFrom:
      moduleMetadata:
        group: ray-on-eks
        name: ray-on-eks
        key: EksServiceAccountName
```
