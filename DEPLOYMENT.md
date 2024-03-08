# Deployment Guide

## Set-up the environment(s)

1. Clone the repository and checkout a release branch using the below command:

```
git clone --origin upstream --branch release/1.0.0 https://github.com/awslabs/mlops-modules
```
The release version can be replaced with the version of interest.

2. Move into the `mlops-modules` repository:
```
cd mlops-modules
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

5. Bbootstrap the CDK environment (one time per region) with CDK V2. Asuming you are deploying in `us-east-1`:
```
cdk bootstrap aws://${PRIMARY_ACCOUNT}/us-east-1
```
6. Bootstrap AWS Account(s)

Assuming that you will be using a single account, follow the guide [here](https://seed-farmer.readthedocs.io/en/latest/bootstrapping.html#) to bootstrap your account(s) to function as a toolchain and target account.

Following is the command to bootstrap your existing account to a toolchain and target account.
```
seedfarmer bootstrap toolchain --project mlops --trusted-principal ${ADMIN_ROLE_ARN} --as-target
```

## Deployment

Note: if you are deploying into a region different from `us-east-1`, change the `regionMappings` in `manifests/deployment.yaml`.
```
seedfarmer apply manifests/deployment.yaml
```
## Clean-up

Do destroy all modules, run:
```
seedfarmer destroy mlops
```
