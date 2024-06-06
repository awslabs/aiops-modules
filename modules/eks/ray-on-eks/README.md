# Ray on EKS

## Description

This module runs Ray in AWS EKS Kubernetes cluster. It deploys a KubeRay Operator via [kuberay-helm](https://github.com/ray-project/kuberay-helm) and supports Custom Resource manifests mounted via `dataFiles`.

### Usage

## RayJob Example

This example leverages [RayJob](https://docs.ray.io/en/latest/cluster/kubernetes/getting-started/rayjob-quick-start.html). 
With RayJob, KubeRay automatically creates a RayCluster and submits a job when the cluster is ready. 
You can also configure RayJob to automatically delete the RayCluster once the Ray job finishes. 

1. Make sure ray-job manifest dataFile and CustomManifestPaths is provided and deploy the module:
```
name: ray-on-eks
path: modules/eks/ray-on-eks
dataFiles:
  - filePath: data/ray/ray-job.shutdown.yaml

...

  - name: CustomManifestPaths
    value:
    - data/ray/ray-job.shutdown.yaml

```
2. Connect to EKS cluster
```
aws eks update-kubeconfig --region us-east-1 --name eks-cluster-xxx
```
3. Check that job has been submitted successfully:

```
kubectl get pods --all-namespaces

NAMESPACE     NAME                                                       READY   STATUS              RESTARTS   AGE
...

ray           rayjob-sample-shutdown-xxxxx                               0/1     Completed           0          4m21s
```
4. Retrieve job logs after completion:

```
kubectl logs -n ray rayjob-sample-shutdown-xxxxx

...
test_counter got 1
test_counter got 2
test_counter got 3
test_counter got 4
test_counter got 5
2024-06-05 07:27:08,908 SUCC cli.py:60 -- --------------------------------------------
2024-06-05 07:27:08,908 SUCC cli.py:61 -- Job 'rayjob-sample-shutdown-xxx' succeeded
2024-06-05 07:27:08,908 SUCC cli.py:62 -- --------------------------------------------

```

## RayCluster Example

The example leverages [RayCluster](https://docs.ray.io/en/latest/cluster/kubernetes/getting-started/raycluster-quick-start.html).

After deploying the RayCluster, follow the steps below to submit a job to the cluster.

1. Make sure ray-cluster manifest dataFile and CustomManifestPaths is provided and deploy the module:
```
name: ray-on-eks
path: modules/eks/ray-on-eks
dataFiles:
  - filePath: data/ray/ray-cluster.autoscaler.yaml

...

  - name: CustomManifestPaths
    value:
    - data/ray/ray-cluster.autoscaler.yaml

```
2. Connect to EKS cluster
```
aws eks update-kubeconfig --region us-east-1 --name eks-cluster-xxx
```

3. Check that Ray cluster and operator pods are running:

```
kubectl get pods --all-namespaces

NAMESPACE     NAME                                                        READY   STATUS    RESTARTS   AGE
...
ray           kuberay-operator-...                                        1/1     Running   0          11m
ray           ray-cluster-kuberay-head-...                                1/1     Running   0          11m
ray           ray-cluster-kuberay-worker-workergroup-...                  1/1     Running   0          11m
ray           ray-cluster-kuberay-worker-workergroup-...                  1/1     Running   0          11m
```

4.Set up port forwarding:

```
kubectl port-forward -n ray --address 0.0.0.0 ray-cluster-kuberay-head-...  8265:8265
```

5. Submit a Ray job:
```
ray job submit --address http://localhost:8265 -- python -c "import ray; ray.init(); print(ray.cluster_resources())"
```

## Inputs/Outputs

### Input Parameters

#### Required

- `eks_cluster_name` - Name of the EKS cluster to deploy to
- `eks_cluster_admin_role_arn`- ARN of EKS admin role to authenticate kubectl
- `eks_oidc_arn` - ARN of EKS OIDC provider for IAM roles
- `eks_openid_issuer` - OIDC issuer
- `eks_cluster_endpoint` - EKS cluster endpoint
- `eks_cert_auth_data` - Auth certificate
- `namespace` - Kubernetes namespace name

#### Optional

- `custom_manifest_paths` - paths mounted via dataFiles that contain custom manifests
- `tags` - List of additional tags to apply to all resources

### Sample manifest declaration

```yaml
name: ray-on-eks
path: modules/eks/ray-on-eks
dataFiles:
  - filePath: data/ray/ray-cluster.autoscaler.yaml
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
  - name: EksOpenidIssuer
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterOpenIdConnectIssuer
  - name: EksCertAuthData
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterCertAuthData
  - name: EksClusterSecurityGroupId
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterSecurityGroupId
  - name: Namespace
    valueFrom:
      parameterValue: rayNamespaceName
  - name: CustomManifestPath
    value: data/ray/ray-cluster.autoscaler.yaml
```

### Module Metadata Outputs

- `EksServiceAccountRoleArn`: Service Account Role ARN.
- `NamespaceName`: Name of the namespace.

