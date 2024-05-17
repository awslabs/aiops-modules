# Ray on EKS

## Description

This module runs Ray in AWS EKS Kubernetes cluster.

### Usage

After deploying the module, follow the steps below to submit a job.

1. Connect to EKS cluster
```
aws eks update-kubeconfig --region us-east-1 --name mlops-ray-on-eks-core-eks-cluster
```

2. Check that Ray cluster and operator pods are running:

```
kubectl get pods --all-namespaces

NAMESPACE     NAME                                                        READY   STATUS    RESTARTS   AGE
...
ray           kuberay-operator-...                                        1/1     Running   0          11m
ray           ray-cluster-kuberay-head-...                                1/1     Running   0          11m
ray           ray-cluster-kuberay-worker-workergroup-...                  1/1     Running   0          11m
ray           ray-cluster-kuberay-worker-workergroup-...                  1/1     Running   0          11m
```

3. Set up port forwarding:

```
kubectl port-forward -n ray --address 0.0.0.0 ray-cluster-kuberay-head-...  8265:8265
```

4. Submit a Ray job:
```
ray job submit --address http://localhost:8265 -- python -c "import ray; ray.init(); print(ray.cluster_resources())"
```

## Inputs/Outputs

### Input Parameters

#### Required

- `eks_cluster_name`
- `eks_cluster_admin_role_arn`
- `eks_oidc_arn`
- `eks_openid_issuer`
- `eks_cluster_endpoint`
- `eks_cert_auth_data`
- `namespace`

#### Optional

- `tags`: additional tags to apply to all resources

### Sample manifest declaration

```yaml
name: ray-on-eks
path: modules/eks/ray-on-eks
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
```

### Module Metadata Outputs

- `EksServiceAccountRoleArn`: Service Account Role ARN.
- `NamespaceName`: Name of the namespace.

