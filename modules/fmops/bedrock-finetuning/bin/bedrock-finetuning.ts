#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { AmazonBedrockFinetuningStack } from "../lib/bedrock-finetuning-stack";
import "source-map-support/register";
import * as cdk_nag from "cdk-nag";

const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION;

const projectName = process.env.SEEDFARMER_PROJECT_NAME;
const deploymentName = process.env.SEEDFARMER_DEPLOYMENT_NAME;
const moduleName = process.env.SEEDFARMER_MODULE_NAME;

const vpcId: string | undefined = process.env.SEEDFARMER_PARAMETER_VPC_ID;
const subnetIds: string[] = JSON.parse(
  process.env.SEEDFARMER_PARAMETER_SUBNET_IDS || ("[]" as string),
);
const bedrockBaseModelID: string =
  process.env.SEEDFARMER_PARAMETER_BEDROCK_BASE_MODEL_ID!;
const bucketName: string | undefined =
  process.env.SEEDFARMER_PARAMETER_BUCKET_NAME;

const removalPolicy =
  process.env.SEEDFARMER_PARAMETER_REMOVAL_POLICY?.toUpperCase() ?? "RETAIN";
if (removalPolicy != "RETAIN" && removalPolicy != "DESTROY") {
  throw new Error("Invalid removal policy for resources");
}

const app = new cdk.App();
const stack = new AmazonBedrockFinetuningStack(
  app,
  `${projectName}-${deploymentName}-${moduleName}`,
  {
    bedrockBaseModelID,
    vpcId,
    subnetIds,
    projectName,
    deploymentName,
    moduleName,
    bucketName,
    removalPolicy,
    env: { account, region },
  },
);

new cdk.CfnOutput(stack, "metadata", {
  value: JSON.stringify({
    BucketName: stack.bucketName,
  }),
});

cdk.Aspects.of(app).add(new cdk_nag.AwsSolutionsChecks({ logIgnores: true }));

app.synth();
