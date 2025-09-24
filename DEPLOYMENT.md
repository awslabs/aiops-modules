# Deployment Guide

## Set-up the environment(s)

1. Clone the repository and checkout a release branch using the below command:

```
git clone --origin upstream --branch release/2.0.0 https://github.com/awslabs/aiops-modules
```
The release version can be replaced with the version of interest.

2. Move into the `aiops-modules` repository:
```
cd aiops-modules
```
3. Create and activate a Virtual environment
```
python3 -m venv .venv && source .venv/bin/activate
```
4. Install the requirements
```
pip install -r ./requirements.txt
```
5. Set environment variables

Replace the values below with your AWS account id and Administrator IAM Role.
```
export PRIMARY_ACCOUNT=XXXXXXXXXXXX
export ADMIN_ROLE_ARN=arn:aws:iam::XXXXXXXXXXXX:role/XXXXX
```

5. Bootstrap the CDK environment (one time per region) with CDK V2. Assuming you are deploying in `us-east-1`:
```
cdk bootstrap aws://${PRIMARY_ACCOUNT}/us-east-1
```
6. Bootstrap AWS Account(s)

Assuming that you will be using a single account, follow the guide [here](https://seed-farmer.readthedocs.io/en/latest/bootstrapping.html#) to bootstrap your account(s) to function as a toolchain and target account.

Following is the command to bootstrap your existing account to a toolchain and target account.
```
seedfarmer bootstrap toolchain --project aiops --trusted-principal ${ADMIN_ROLE_ARN} --as-target
```

## Deployment

Pick the manifest to deploy. Manifests are located in `manifests/` directory. For example, to deploy SageMaker mlops manifests, run:

!Note: if you are deploying into a region different from `us-east-1`, change the `regionMappings` in `deployment.yaml`.
```
seedfarmer apply manifests/mlops-sagemaker/deployment.yaml
```

To deploy an uber-manifest containing all modules, run:

Note: this is an uber-manifest that contains all modules. It may take a while to deploy.
```
seedfarmer apply manifests/uber-deployment.yaml
```
## Clean-up

Do destroy all modules, run:
```
seedfarmer destroy mlops
```
