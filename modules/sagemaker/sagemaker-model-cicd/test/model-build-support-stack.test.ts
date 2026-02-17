import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { ModelBuildSupportStack } from '../lib';

const baseProps = {
  projectName: 'test-project',
  toolingEnvironment: {
    account: '123456789012',
    region: 'us-east-1',
  },
  sagemakerArtifactsBucketName: 'sagemaker-artifacts-bucket',
  sagemakerExecutionRoleName: 'sagemaker-execution-role',
  modelPackageGroupName: 'model-package-group',
  codeBuildRoleName: 'code-build-role',
  modelApprovalTopicName: 'model-approval-topic',
  deployEnvironments: [
    {
      name: 'gamma-env',
      account: '123456789013',
      type: 'preprod' as const,
    },
    {
      name: 'prod-env',
      account: '123456789014',
      type: 'prod' as const,
    },
  ],
};

test('ModelBuildSupportStack to match snapshot', () => {
  const app = new cdk.App();
  const stack = new ModelBuildSupportStack(app, 'MyTestStack', baseProps);
  const template = Template.fromStack(stack);
  expect(template.toJSON()).toMatchSnapshot();
});

test('ModelBuildSupportStack with s3AccessLogsBucketArn configures logging on LogsBucket', () => {
  const app = new cdk.App();
  const stack = new ModelBuildSupportStack(app, 'MyTestStack', {
    ...baseProps,
    s3AccessLogsBucketArn: 'arn:aws:s3:::test-access-logs-bucket',
  });
  const template = Template.fromStack(stack);

  // LogsBucket should have LoggingConfiguration with the project-scoped prefix
  template.hasResourceProperties('AWS::S3::Bucket', {
    LoggingConfiguration: {
      DestinationBucketName: 'test-access-logs-bucket',
      LogFilePrefix: 'sagemaker-artifacts-bucket-logs/',
    },
  });
});

test('ModelBuildSupportStack without s3AccessLogsBucketArn has no LoggingConfiguration on LogsBucket', () => {
  const app = new cdk.App();
  const stack = new ModelBuildSupportStack(app, 'MyTestStack', baseProps);
  const template = Template.fromStack(stack);

  // The LogsBucket should NOT have a LoggingConfiguration (only ArtifactsBucket logs to LogsBucket)
  const buckets = template.findResources('AWS::S3::Bucket');
  /* eslint-disable @typescript-eslint/no-explicit-any */
  const logsBucket = Object.values(buckets).find(
    (b: any) => !b.Properties.BucketName,
  );
  /* eslint-enable @typescript-eslint/no-explicit-any */
  expect(
    logsBucket?.Properties.LoggingConfiguration?.DestinationBucketName,
  ).toBeUndefined();
});
