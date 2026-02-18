import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { MLOpsCodePipelineStack } from '../lib';

const baseProps = {
  env: { account: '123456789011', region: 'us-east-1' }, // tooling account
  projectName: 'TestProject',
  deploymentGroups: [
    // experimenation deployment group to train model on test dataset
    {
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
    // prod deployment group with retraining on prod dataset
    {
      name: 'prod-deployment-group',
      sourceBranch: 'main',
      buildEnvironment: {
        name: 'prod-train-env',
        account: '123456789015',
        region: 'us-east-1',
        type: 'preprod' as const,
      },
      deployEnvironments: [
        {
          name: 'prod-approval-env',
          account: '123456789016',
          type: 'preprod' as const,
        },
        {
          name: 'prod-env',
          account: '123456789017',
          type: 'prod' as const,
        },
      ],
    },
  ],
  modelBuildRepo: {
    host: 'codecommit' as const,
    name: 'model-build-repo',
  },
  infraRepo: {
    host: 'codecommit' as const,
    name: 'model-deploy-repo',
    branch: 'main',
  },
};

test('MLOpsCodePipelineStack to match snapshot', () => {
  const app = new cdk.App();
  const stack = new MLOpsCodePipelineStack(app, 'MyTestStack', baseProps);
  const template = Template.fromStack(stack);
  expect(template.toJSON()).toMatchSnapshot();
});

test('MLOpsCodePipelineStack with s3AccessLogsBucketArn configures logging on artifact bucket', () => {
  const app = new cdk.App();
  const stack = new MLOpsCodePipelineStack(app, 'MyTestStack', {
    ...baseProps,
    s3AccessLogsBucketArn: 'arn:aws:s3:::test-access-logs-bucket',
  });
  const template = Template.fromStack(stack);

  template.hasResourceProperties('AWS::S3::Bucket', {
    LoggingConfiguration: {
      DestinationBucketName: 'test-access-logs-bucket',
      LogFilePrefix: 'TestProject-infra-pipeline-artifacts/',
    },
  });
});
