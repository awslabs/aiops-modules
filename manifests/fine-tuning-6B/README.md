# How to fine tune a 6B LLM on Ray on Amazon Elastic Kubernetes Service

## Description

The manifest `manifests/fine-tuning-6B/deployment.yaml` deploys Ray on Amazon EKS.

It provisions an [Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html) cluster with 2 node groups: 
Core (CPU) and Workload (GPU) and deploys [KubeRay](https://github.com/ray-project/kuberay) Ray Operator, and a Ray Cluster 
with autoscaling and mounted high-performance [Amazon FSx for Lustre](https://docs.aws.amazon.com/fsx/latest/LustreGuide/what-is.html)
file system. Additionally, a custom Ray container image is supported.

### Architecture

![Ray on Amazon EKS Architecture](docs/ray-on-eks-architecture.jpg "Ray on Amazon EKS Architecture")

### Modules Inventory

- [Ray Operator Module](modules/eks/ray-operator/README.md)
- [Ray Cluster Module](modules/eks/ray-cluster/README.md)
- [Ray Image Module](modules/eks/ray-image/README.md)
- [EKS Module](https://github.com/awslabs/idf-modules/tree/main/modules/compute/eks)
- [FSx for Lustre Module](https://github.com/awslabs/idf-modules/tree/main/modules/storage/fsx-lustre)
- [FSx for Lustre on EKS Integration Module](https://github.com/awslabs/idf-modules/tree/main/modules/integration/fsx-lustre-on-eks)
- [Networking Module](https://github.com/awslabs/idf-modules/tree/main/modules/network/basic-cdk)
- [ECR Module](https://github.com/awslabs/idf-modules/tree/main/modules/storage/ecr)
- [Buckets  Module](https://github.com/awslabs/idf-modules/tree/main/modules/storage/buckets)

## Deployment

For deployment instructions, please refer to [DEPLOYMENT.MD](https://github.com/awslabs/aiops-modules/blob/main/DEPLOYMENT.md).

## User Guide

### Submitting Jobs

After deploying the manifest, follow the steps below to submit a job to the cluster.

1. Connect to EKS cluster
```
aws eks update-kubeconfig --region us-east-1 --name eks-cluster-xxx
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

3. Check Ray service is running:

```
kubectl get services -n ray

NAME               TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)                                         AGE
kuberay-head-svc   ClusterIP   ...              <none>        10001/TCP,8265/TCP,8080/TCP,6379/TCP,8000/TCP   64s
kuberay-operator   ClusterIP   ...              <none>        8080/TCP                                        6m3s
```

4. Get Ray service endpoint:

```
kubectl get endpoints -n ray

NAME               ENDPOINTS                                                      AGE
kuberay-head-svc   ...:8080,...:10001,...:8000 + 2 more...                        98s
kuberay-operator   ...:8080                                                       6m37s
```

5. Set up port forwarding:

```
kubectl port-forward -n ray --address 0.0.0.0 service/kuberay-head-svc  8265:8265
```

6. Submit the job:

```
ray job submit --address http://localhost:8265 --working-dir="." -- python scripts/training-6B.py
```

9. Access the Ray Dashboard at `http://localhost:8265`:

![Ray Dashboard](docs/ray-dashboard.png "Ray Dashboard")
