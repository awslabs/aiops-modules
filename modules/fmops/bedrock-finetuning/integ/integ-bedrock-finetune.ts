import * as cdk from "aws-cdk-lib";
import * as cloud_assembly_schema from "aws-cdk-lib/cloud-assembly-schema";
import * as integ_tests_alpha from "aws-cdk-lib/integ-tests-alpha";

import { SSM } from "aws-sdk";

import { AmazonBedrockFinetuningStack } from "../lib/bedrock-finetuning-stack";


function getModuleDependencies(resourceKeys: string[]): Record<string, string> {
  const ssmClient = new SSM({ region: "us-east-1" });
  const dependencies: Record<string, string> = {};

  for (const key of resourceKeys) {
    const paramPromise = ssmClient.getParameter({
      Name: `/module-integration-tests/${key}`,
    }).promise();

    paramPromise.then(
      (param) => {
        dependencies[key] = param.Parameter?.Value as string;
      },
      (err) => {
        console.error(`Error retrieving parameter: ${err}`);
      },
    );
  }

  return dependencies;
}


describe("Bedrock Finetuning Stack", () => {
  const app = new cdk.App();

  const dependencies = getModuleDependencies(["vpc-id", "vpc-private-subnets"]);
  const vpcId = dependencies["vpc-id"];
  const subnetIds = JSON.parse(dependencies["vpc-private-subnets"]);

  const stack = new AmazonBedrockFinetuningStack(
    app,
    "bedrock-finetuning-integ-stack",
    {
      vpcId,
      subnetIds,
      bedrockBaseModelID: "amazon.titan-text-express-v1:0:8k",
      projectName: "test-project",
      deploymentName: "test-deployment",
      moduleName: "test-module",
      removalPolicy: "DESTROY",
      env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: "us-east-1" },
    },
  );

  new integ_tests_alpha.IntegTest(app, "Integration Tests Bedrock Finetuning Module", {
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
  });
});
