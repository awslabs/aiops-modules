import * as cdk from "aws-cdk-lib";
import * as cloud_assembly_schema from "aws-cdk-lib/cloud-assembly-schema";
import * as integ_tests_alpha from "@aws-cdk/integ-tests-alpha";

import { SSM } from "aws-sdk";

import { AmazonBedrockFinetuningStack } from "../lib/bedrock-finetuning-stack";

async function retrieveValueFromSSMParameter(
  parameterName: string,
): Promise<string> {
  const ssmClient = new SSM({ region: "us-east-1" });
  const param = await ssmClient
    .getParameter({
      Name: `/module-integration-tests/${parameterName}`,
    })
    .promise();

  const value = param.Parameter?.Value;
  if (!value) {
    throw new Error(`Parameter ${parameterName} not found`);
  }

  return value;
}

const app = new cdk.App();

const vpcId = await retrieveValueFromSSMParameter("vpc-id");
const subnetIds = await retrieveValueFromSSMParameter("vpc-private-subnets");
const stack = new AmazonBedrockFinetuningStack(
  app,
  "bedrock-finetuning-integ-stack",
  {
    vpcId: vpcId,
    subnetIds: JSON.parse(subnetIds),
    bedrockBaseModelID: "amazon.titan-text-express-v1:0:8k",
    projectName: "test-project",
    deploymentName: "test-deployment",
    moduleName: "test-module",
    removalPolicy: "DESTROY",
    env: { region: "us-east-1" },
  },
);

new integ_tests_alpha.IntegTest(
  app,
  "Integration Tests Bedrock Finetuning Module",
  {
    testCases: [stack],
    diffAssets: true,
    stackUpdateWorkflow: true,
    enableLookups: true,
    cdkCommandOptions: {
      deploy: {
        args: {
          requireApproval: cloud_assembly_schema.RequireApproval.NEVER,
          json: true,
        },
      },
      destroy: {
        args: {
          force: true,
        },
      },
    },
  },
);

app.synth();
