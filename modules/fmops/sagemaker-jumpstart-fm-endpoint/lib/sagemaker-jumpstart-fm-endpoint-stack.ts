import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import { Vpc, SecurityGroup } from "aws-cdk-lib/aws-ec2";
import { Effect, PolicyDocument, PolicyStatement, Role, ServicePrincipal } from "aws-cdk-lib/aws-iam";
import { CfnModel } from "aws-cdk-lib/aws-sagemaker";
import {
  JumpStartModel,
  SageMakerInstanceType,
  JumpStartSageMakerEndpoint,
} from "@cdklabs/generative-ai-cdk-constructs";
import * as cdk_nag from "cdk-nag";

interface SagemakerJumpStartFmEndpointStackProps extends cdk.StackProps {
  projectName?: string;
  deploymentName?: string;
  moduleName?: string;
  jumpStartModelName: string;
  instanceType: string;
  vpcId?: string | undefined;
  subnetIds: string[];
}

export class SagemakerJumpStartFmEndpointStack extends cdk.Stack {
  jumpStartEndpoint: JumpStartSageMakerEndpoint;
  role: Role;

  constructor(scope: Construct, id: string, props: SagemakerJumpStartFmEndpointStackProps) {
    super(scope, id, props);

    this.role = new Role(this, "Role", {
      assumedBy: new ServicePrincipal("sagemaker.amazonaws.com"),
      // managedPolicies: [
      //   ManagedPolicy.fromAwsManagedPolicyName("AmazonSageMakerFullAccess"),
      // ],
      inlinePolicies: {
        inline: new PolicyDocument({
          statements: [
            new PolicyStatement({
              effect: Effect.ALLOW,
              actions: ["s3:GetObject", "s3:ListBucket"],
              resources: ["arn:aws:s3:::jumpstart-*"],
            }),
            new PolicyStatement({
              effect: Effect.ALLOW,
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

    let vpcConfig: CfnModel.VpcConfigProperty | undefined = undefined;

    if (props.vpcId) {
      const vpc = Vpc.fromLookup(this, "Vpc", { vpcId: props.vpcId });
      const securityGroup = new SecurityGroup(this, "SecurityGroup", {
        vpc: vpc,
      });
      vpcConfig = {
        securityGroupIds: [securityGroup.securityGroupId],
        subnets: props.subnetIds,
      };
    }

    this.jumpStartEndpoint = new JumpStartSageMakerEndpoint(this, "JumpStartEndpoint", {
      model: JumpStartModel.of(props.jumpStartModelName),
      instanceType: SageMakerInstanceType.of(props.instanceType),
      role: this.role,
      vpcConfig: vpcConfig,
    });

    cdk_nag.NagSuppressions.addResourceSuppressions(this.role, [
      {
        id: "AwsSolutions-IAM5",
        reason: "Resource access restriced to S3 buckets (with a prefix) and ECR images",
      },
    ]);
  }
}
