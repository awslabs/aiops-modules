import * as cdk from "aws-cdk-lib";
import { Annotations, Match, Template } from "aws-cdk-lib/assertions";
import { SagemakerHuggingFaceEndpointStack } from "../lib/sagemaker-hugging-face-endpoint-stack";

describe("Sagemaker JumpStart Fm Endpoint Stack", () => {
  const app = new cdk.App();

  const projectName = "mlops";
  const deploymentName = "platform";
  const moduleName = "fm-endpoint";
  const huggingFaceModelID = "HUGGINGFACE_LLM_MISTRAL_7B_2_1_0";
  const instanceType = "ml.g5.2xlarge";
  const deepLearningContainerImage =
    "huggingface-pytorch-tgi-inference:2.0.1-tgi1.1.0-gpu-py39-cu118-ubuntu20.04";
  const vpcId = "vpc-123";
  const subnetIds = ["sub1", "sub2"];
  const account = "123456789";
  const region = "us-east-1";

  const stack = new SagemakerHuggingFaceEndpointStack(
    app,
    `${projectName}-${deploymentName}-${moduleName}`,
    {
      projectName,
      deploymentName,
      moduleName,
      huggingFaceModelID,
      instanceType,
      vpcId,
      subnetIds,
      env: { account, region },
    },
  );

  test("Synth stack", () => {
    const template = Template.fromStack(stack);

    template.hasResource("AWS::SageMaker::Endpoint", {});
    template.hasResource("AWS::IAM::Role", {});
    template.hasResource("AWS::EC2::SecurityGroup", {});
  });

  test("No CDK Nag Errors", () => {
    const errors = Annotations.fromStack(stack).findError(
      "*",
      Match.stringLikeRegexp("AwsSolutions-.*"),
    );
    expect(errors).toHaveLength(0);
  });
});
