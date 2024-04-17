import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as sagemaker from "aws-cdk-lib/aws-sagemaker";
import {
  DeepLearningContainerImage,
  HuggingFaceSageMakerEndpoint,
  SageMakerInstanceType,
} from "@cdklabs/generative-ai-cdk-constructs";
import * as cdk_nag from "cdk-nag";

interface SagemakerHuggingFaceEndpointStackProps extends cdk.StackProps {
  projectName?: string;
  deploymentName?: string;
  moduleName?: string;
  huggingFaceModelID: string;
  instanceType: string;
  deepLearningContainerImage: string;
  vpcId?: string | undefined;
  subnetIds: string[];
}

export class SagemakerHuggingFaceEndpointStack extends cdk.Stack {
  huggingFaceEndpoint: HuggingFaceSageMakerEndpoint;
  role: iam.Role;

  constructor(scope: Construct, id: string, props: SagemakerHuggingFaceEndpointStackProps) {
    super(scope, id, props);

    this.role = new iam.Role(this, "Role", {
      assumedBy: new iam.ServicePrincipal("sagemaker.amazonaws.com"),
      inlinePolicies: {
        inline: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                "ecr:BatchCheckLayerAvailability",
                "ecr:BatchGetImage",
                "ecr:Describe*",
                "ecr:GetAuthorizationToken",
                "ecr:GetDownloadUrlForLayer",
                "ec2:CreateNetworkInterface",
                "ec2:CreateNetworkInterfacePermission",
                "ec2:CreateVpcEndpoint",
                "ec2:DeleteNetworkInterface",
                "ec2:DeleteNetworkInterfacePermission",
                "ec2:Describe*",
                "logs:CreateLogDelivery",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:DeleteLogDelivery",
                "logs:Describe*",
                "logs:GetLogDelivery",
                "logs:GetLogEvents",
                "logs:ListLogDeliveries",
                "logs:PutLogEvents",
                "logs:PutResourcePolicy",
                "logs:UpdateLogDelivery",
              ],
              resources: ["*"],
            }),
          ],
        }),
      },
    });

    let vpcConfig: sagemaker.CfnModel.VpcConfigProperty | undefined = undefined;

    if (props.vpcId) {
      const vpc = ec2.Vpc.fromLookup(this, "Vpc", { vpcId: props.vpcId });
      const securityGroup = new ec2.SecurityGroup(this, "SecurityGroup", {
        vpc: vpc,
      });
      vpcConfig = {
        securityGroupIds: [securityGroup.securityGroupId],
        subnets: props.subnetIds,
      };
    }

    const [containerImageRepoName, containerImageTag] = SagemakerHuggingFaceEndpointStack.parseContainerImage(
      props.deepLearningContainerImage,
    );

    this.huggingFaceEndpoint = new HuggingFaceSageMakerEndpoint(this, "HuggingFace Endpoint", {
      modelId: props.huggingFaceModelID,
      instanceType: SageMakerInstanceType.of(props.instanceType),
      container: DeepLearningContainerImage.fromDeepLearningContainerImage(containerImageRepoName, containerImageTag),
      role: this.role,
      vpcConfig: vpcConfig,
    });

    cdk_nag.NagSuppressions.addResourceSuppressions(
      this.role,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "Resource access restriced to S3 buckets (with a prefix) and ECR images",
        },
      ],
      true,
    );
  }

  static parseContainerImage(deepLearningContainerImage: string): [string, string] {
    const parts = deepLearningContainerImage.split(":");
    if (parts.length !== 2) {
      throw new Error(`Invalid container image: ${deepLearningContainerImage}`);
    }

    return [parts[0], parts[1]];
  }
}
