import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { SagemakerJumpStartFmEndpointStack } from "./lib/sagemaker-jumpstart-fm-endpoint-stack";

const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION;

const projectName = process.env.SEEDFARMER_PROJECT_NAME;
const deploymentName = process.env.SEEDFARMER_DEPLOYMENT_NAME;
const moduleName = process.env.SEEDFARMER_MODULE_NAME;

const jumpStartModelName: string = process.env.SEEDFARMER_PARAMETER_JUMP_START_MODEL_NAME!;
const instanceType: string = process.env.SEEDFARMER_PARAMETER_INSTANCE_TYPE!;

const vpcId: string | undefined = process.env.SEEDFARMER_PARAMETER_VPC_ID;
const subnetIds: string[] = JSON.parse(process.env.SEEDFARMER_PARAMETER_SUBNET_IDS || ("[]" as string));

const app = new cdk.App();

const stack = new SagemakerJumpStartFmEndpointStack(app, `${projectName}-${deploymentName}-${moduleName}`, {
  projectName,
  deploymentName,
  moduleName,
  jumpStartModelName,
  instanceType,
  vpcId,
  subnetIds,
  env: { account, region },
});

new cdk.CfnOutput(stack, "metadata", {
  value: JSON.stringify({
    EndpointArn: stack.jumpStartEndpoint.endpointArn,
    RoleArn: stack.role.roleArn,
  }),
});

app.synth();
