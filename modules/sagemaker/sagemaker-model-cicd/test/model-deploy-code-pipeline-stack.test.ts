import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { ModelDeployCodePipelineStack } from '../lib';

const baseProps = {
  projectName: 'test-project',
  deploymentGroup: {
    name: 'experimenation-deployment-group',
    sourceBranch: 'dev',
    buildEnvironment: {
      name: 'experiment-env1',
      account: '123456789012',
      region: 'us-east-1',
      type: 'dev' as const,
    },
    deployEnvironments: [
      {
        name: 'experiment-env2',
        account: '123456789013',
        type: 'dev' as const,
      },
      {
        name: 'experiment-env3',
        account: '123456789014',
        type: 'dev' as const,
      },
    ],
  },
  modelApprovalTopicName: 'model-approval-topic',
  modelBuildRepositoryName: 'model-build-repo',
  infraRepo: {
    host: 'codecommit' as const,
    name: 'infra-repo',
    branch: 'main',
  },
  modelPackageGroupName: 'model-package-group',
  ssmParamName: 'ssm-param',
  sagemakerArtifactsBucketName: 'sagemaker-artifacts-bucket',
};

test('ModelDeployCodePipelineStack to match snapshot', () => {
  const app = new cdk.App();
  const stack = new ModelDeployCodePipelineStack(app, 'MyTestStack', baseProps);
  const template = Template.fromStack(stack);
  expect(template.toJSON()).toMatchSnapshot();
});

test('ModelDeployCodePipelineStack with s3AccessLogsBucketArn configures logging on artifact bucket', () => {
  const app = new cdk.App();
  const stack = new ModelDeployCodePipelineStack(app, 'MyTestStack', {
    ...baseProps,
    s3AccessLogsBucketArn: 'arn:aws:s3:::test-access-logs-bucket',
  });
  const template = Template.fromStack(stack);

  template.hasResourceProperties('AWS::S3::Bucket', {
    LoggingConfiguration: {
      DestinationBucketName: 'test-access-logs-bucket',
      LogFilePrefix: 'test-project-dev-deploy-artifacts/',
    },
  });
});
