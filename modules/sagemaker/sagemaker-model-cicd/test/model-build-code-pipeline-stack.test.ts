import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { ModelBuildCodePipelineStack } from '../lib';

const baseProps = {
  projectName: 'test-project',
  sourceBranch: 'main',
  modelBuildEnvironment: {
    name: 'model-build',
    account: '123456789012',
    region: 'us-east-1',
    type: 'dev' as const,
  },
  modelBuildSourceRepoName: 'model-build-repo',
  sagemakerArtifactsBucketName: 'sagemaker-artifacts-bucket',
  sagemakerExecutionRoleName: 'sagemaker-execution-role',
  codeBuildAssumeRoleName: 'codebuild-assume-role',
  modelPackageGroupName: 'model-package-group',
};

test('ModelBuildCodePipelineStack to match snapshot', () => {
  const app = new cdk.App();
  const stack = new ModelBuildCodePipelineStack(app, 'MyTestStack', baseProps);
  const template = Template.fromStack(stack);
  expect(template.toJSON()).toMatchSnapshot();
});

test('ModelBuildCodePipelineStack with s3AccessLogsBucketArn configures logging on artifact bucket', () => {
  const app = new cdk.App();
  const stack = new ModelBuildCodePipelineStack(app, 'MyTestStack', {
    ...baseProps,
    s3AccessLogsBucketArn: 'arn:aws:s3:::test-access-logs-bucket',
  });
  const template = Template.fromStack(stack);

  template.hasResourceProperties('AWS::S3::Bucket', {
    LoggingConfiguration: {
      DestinationBucketName: 'test-access-logs-bucket',
      LogFilePrefix: 'test-project-main-build-artifacts/',
    },
  });
});
