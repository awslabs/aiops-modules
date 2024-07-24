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

- `enable_autoscaling` - Whether ray autoscaler is enabled. `True` by default.
- `autoscaler_idle_timeout_seconds` -  The number of seconds to wait before scaling down a worker pod which is not using Ray resources.
- `head_resources` - Head group resource requests and limits. Defaults to:
```yaml
      requests:
        cpu: "1"
        memory: "8G"
      limits:
        cpu: "1"
        memory: "8G"
```
- `worker_replicas` - The requested number of the Pod replicas in worker group. Defaults to `1`.
- `worker_min_replicas` - The minimum number of the Pod replicas in worker group. Defaults to `1`.
- `worker_max_replicas` - The maximum number of the Pod replicas in worker group. Defaults to `10`.
- `worker_resources` - Worker group resource requests and limits. Defaults to:
```yaml
      requests:
        cpu: "1"
        memory: "8G"
      limits:
        cpu: "1"
        memory: "8G"
```
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
        group: ray-operator
        name: ray-operator
        key: EksServiceAccountName
  - name: HeadResources
    value:
      requests:
        cpu: "1"
        memory: "8G"
      limits:
        cpu: "1"
        memory: "8G"
  - name: WorkerReplicas
    value: 2
  - name: WorkerMinReplicas
    value: 2
  - name: WorkerMaxReplicas
    value: 10
  - name: WorkerResources
    value:
      requests:
        cpu: "4"
        memory: "24G"
      limits:
        cpu: "4"
        memory: "24G"
```
