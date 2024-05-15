import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as kms from "aws-cdk-lib/aws-kms";

export class MlopsModulesDevelopmentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // create S3 bucket
    const inputBucket = new s3.Bucket(this, "BedrockBucket", {
      bucketName: "bedrock-input-data-lj",
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      eventBridgeEnabled: true,
    });

    // Create a KMS Key
    const key = new kms.Key(this, "MyKey", {
      enableKeyRotation: true,
      description: "Key for encrypting Bedrock fine-tuning jobs",
    });

    // creating IAM role to pass to Amazon Bedrock
    const bedrockS3PolicyStatement = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      resources: [inputBucket.bucketArn, `${inputBucket.bucketArn}/*`],
      conditions: {
        StringEquals: {
          "aws:PrincipalAccount": this.account,
        },
      },
    });
    const bedrockPassRolePolicyStatement = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ["iam:PassRole"],
      resources: ["*"],
      conditions: {
        StringEquals: {
          "aws:PrincipalAccount": this.account,
        },
      },
    });
    const KMSKeyPolicyStatement = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ["kms:*"],
      resources: [key.keyArn],
      conditions: {
        StringEquals: {
          "aws:PrincipalAccount": this.account,
        },
      },
    });

    const bedrockPolicy = new iam.Policy(this, "CustomPolicy", {
      statements: [bedrockS3PolicyStatement, bedrockPassRolePolicyStatement],
    });
    const bedrockRole = new iam.Role(this, "MyRole", {
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal("bedrock.amazonaws.com")
          .withConditions({
            StringEquals: {
              "aws:SourceAccount": this.account,
            },
          })
          .withConditions({
            ArnEquals: {
              "aws:SourceArn": `arn:aws:bedrock:${this.region}:${this.account}:model-customization-job/*`,
            },
          }),
      ),
    });
    bedrockRole.attachInlinePolicy(bedrockPolicy);

    // creating lambda function for running the model finetuning job
    const modelFinetuningLambda = new lambda.Function(
      this,
      "ObjectDetectionLambda",
      {
        runtime: lambda.Runtime.PYTHON_3_11,
        code: lambda.Code.fromAsset("src/lambda-functions"),
        timeout: cdk.Duration.seconds(60),
        memorySize: 512,
        handler: "modelFinetuningLambdaCode.lambda_handler",
        functionName: "modelFinetuningLambdaFcn",
        environment: {
          role_arn: bedrockRole.roleArn,
          kms_key_id: key.keyId,
          base_model_id: "amazon.titan-text-express-v1:0:8k",
        },
      },
    );

    modelFinetuningLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:CreateModelCustomizationJob"],
        resources: ["*"],
        conditions: {
          StringEquals: {
            "aws:PrincipalAccount": this.account,
          },
        },
      }),
    );
    modelFinetuningLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["iam:PassRole"],
        resources: [`${bedrockRole.roleArn}`],
        conditions: {
          StringEquals: {
            "aws:PrincipalAccount": this.account,
          },
        },
      }),
    );
    modelFinetuningLambda.addToRolePolicy(KMSKeyPolicyStatement);
    // creating step function that will trigger the lambda function
    const modelFinetuningLambdaTask = new tasks.LambdaInvoke(
      this,
      "ModelFinetuningLambdaTask",
      {
        lambdaFunction: modelFinetuningLambda,
        outputPath: "$.Payload",
      },
    );
    const definition = modelFinetuningLambdaTask.next(
      new sfn.Succeed(this, "Succeed"),
    );
    const stateMachine = new sfn.StateMachine(this, "MyStateMachine", {
      definition: definition,
      timeout: cdk.Duration.minutes(5),
      stateMachineName: "BedrockFinetuning",
    });

    // Grant the state machine permission to invoke the Lambda function
    modelFinetuningLambda.grantInvoke(stateMachine.role);

    const rule = new events.Rule(this, "Rule", {
      eventPattern: {
        source: ["aws.s3"],
        detailType: ["Object Created"],
        detail: {
          bucket: {
            name: ["bedrock-input-data-lj"],
          },
        },
      },
    });

    rule.addTarget(new targets.SfnStateMachine(stateMachine));
  }
}
