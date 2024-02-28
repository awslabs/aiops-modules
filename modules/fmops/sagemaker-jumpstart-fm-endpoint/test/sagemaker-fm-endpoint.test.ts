import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { SagemakerJumpStartFmEndpointStack } from '../lib/sagemaker-jumpstart-fm-endpoint-stack';

test("Synth stack", () => {
    const app = new cdk.App();

    const projectName = "mlops"
    const deploymentName = "platform"
    const moduleName = "fm-endpoint"
    const jumpStartModelName = "HUGGINGFACE_LLM_MISTRAL_7B_2_1_0"
    const instanceType = "ml.g5.2xlarge"
    const vpcId = "vpc-123"
    const subnetIds = ["sub1", "sub2"]
    const account = "123456789"
    const region = "us-east-1"

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

    const template = Template.fromStack(stack);

    template.hasResource("AWS::SageMaker::Endpoint", {});
    template.hasResource("AWS::IAM::Role", {});
    template.hasResource("AWS::EC2::SecurityGroup", {});
});
