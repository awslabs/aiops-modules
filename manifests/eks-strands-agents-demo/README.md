# Deploy demo Weather Agent with Strands and Amazon EKS Auto Mode

## Description

This manifest deploys a demo [Strands](https://strandsagents.com/latest/) Weather Agent on [Amazon EKS Auto Mode](https://aws.amazon.com/eks/auto-mode/).

1. Provision an Amazon EKS Auto Mode Cluster
2. Build Weather Agent Docker image and push into Amazon ECR repository
3. Create and associate Amazon EKS service account permissions to an IAM Role with Amazon Bedrock access
4. Deploy Weather Agent to Amazon EKS using Helm

## Deployment

```
seedfarmer apply manifests/eks-strands-agents-demo/deployment.yaml
```

For full deployment instructions, please refer to [DEPLOYMENT.MD](https://github.com/awslabs/aiops-modules/blob/main/DEPLOYMENT.md).

## User Guide

### Call the Agent

1. Connect to the cluster

```
aws eks update-kubeconfig --name $CLUSTER_NAME
```

2. Port-forward agent service

```
kubectl --namespace default port-forward service/strands-agents-weather 8080:80 &
```
3. Call agent service

```
curl -X POST \
  http://localhost:8080/weather \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "What is the weather in Seattle?"}'
```
```
# Weather in Seattle, Washington

## Current Conditions
**This Afternoon:** Sunny with a high near 73°F. Northwest wind around 6 mph. Precipitation chance: 1%.

## Tonight
**Tonight:** Mostly clear with a low around 54°F. North northeast wind around 6 mph. No precipitation expected.

## Extended Forecast
- **Sunday:** Sunny with a high near 78°F. North northeast wind 3 to 10 mph. No precipitation expected.
- **Sunday Night:** Mostly clear with a low around 58°F.
- **Monday:** Sunny with a high near 82°F. North wind 3 to 9 mph.
- **Monday Night:** Mostly clear with a low around 59°F.
- **Tuesday:** Sunny with a high near 81°F.

## Outlook
The weather in Seattle looks very pleasant for the next several days with sunny skies and comfortable temperatures. Daytime highs will be in the 70s to low 80s, with overnight lows in the mid-to-upper 50s. There is virtually no chance of precipitation through the next few days, making for excellent outdoor conditions.

For Independence Day (July 4th), you can expect sunny conditions with a high near 75°F, perfect for outdoor celebrations and fireworks viewing.
```