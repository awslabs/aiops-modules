import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import * as cdk_nag from "cdk-nag";
import { SagemakerHuggingFaceEndpointStack } from "./lib/sagemaker-hugging-face-endpoint-stack";

const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION;

const projectName = process.env.SEEDFARMER_PROJECT_NAME;
const deploymentName = process.env.SEEDFARMER_DEPLOYMENT_NAME;
const moduleName = process.env.SEEDFARMER_MODULE_NAME;

const huggingFaceModelID: string = process.env.SEEDFARMER_PARAMETER_HUGGING_FACE_MODEL_ID!;
const instanceType: string = process.env.SEEDFARMER_PARAMETER_INSTANCE_TYPE!;
const deepLearningContainerImage: string = process.env.SEEDFARMER_PARAMETER_DEEP_LEARNING_CONTAINER_IMAGE!;

const vpcId: string | undefined = process.env.SEEDFARMER_PARAMETER_VPC_ID;
const subnetIds: string[] = JSON.parse(process.env.SEEDFARMER_PARAMETER_SUBNET_IDS || ("[]" as string));

const hfTokenSecretName: string | undefined = process.env.SEEDFARMER_PARAMETER_HUGGING_FACE_TOKEN_SECRET_NAME;

const permissionsBoundaryName: string | undefined = process.env.SEEDFARMER_PARAMETER_PERMISSIONS_BOUNDARY_NAME;

const app = new cdk.App();

const stack = new SagemakerHuggingFaceEndpointStack(app, `${projectName}-${deploymentName}-${moduleName}`, {
  projectName,
  deploymentName,
  moduleName,
  huggingFaceModelID,
  instanceType,
  deepLearningContainerImage,
  vpcId,
  subnetIds,
  hfTokenSecretName,
  permissionsBoundaryName,
  env: { account, region },
});

new cdk.CfnOutput(stack, "metadata", {
  value: JSON.stringify({
    EndpointArn: stack.huggingFaceEndpoint.endpointArn,
    RoleArn: stack.role.roleArn,
  }),
});

cdk.Aspects.of(app).add(new cdk_nag.AwsSolutionsChecks({ logIgnores: true }));

app.synth();
