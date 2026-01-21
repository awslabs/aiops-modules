import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import * as eks from 'aws-cdk-lib/aws-eks';
import { HyperpodEksStack } from '../lib/hyperpod-eks-stack';

describe('HyperpodEksStack', () => {
  let app: cdk.App;
  let stack: HyperpodEksStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();
    stack = new HyperpodEksStack(app, 'TestStack', {
      resourceNamePrefix: 'test-hyperpod-eks',
      vpcCidr: '10.192.0.0/16',
      kubernetesVersion: eks.KubernetesVersion.V1_31,
      instanceGroups: {
        'test-group': {
          instanceType: 'ml.g5.2xlarge',
          instanceCount: 2,
          ebsVolumeSize: 50,
          threadsPerCore: 1,
          enableStressCheck: true,
          enableConnectivityCheck: false,
          lifecycleScript: 'test_script.sh',
        },
      },
    });
    template = Template.fromStack(stack);
  });

  test('VPC is created with correct configuration', () => {
    template.hasResourceProperties('AWS::EC2::VPC', {
      CidrBlock: '10.192.0.0/16',
      EnableDnsHostnames: true,
      EnableDnsSupport: true,
    });
  });

  test('EKS cluster is created', () => {
    template.hasResourceProperties('Custom::AWSCDK-EKS-Cluster', {
      Config: {
        version: '1.31',
      },
    });
  });

  test('S3 bucket is created with encryption', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      BucketEncryption: {
        ServerSideEncryptionConfiguration: [
          {
            ServerSideEncryptionByDefault: {
              SSEAlgorithm: 'AES256',
            },
          },
        ],
      },
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      },
    });
  });

  test('SageMaker execution role is created', () => {
    template.hasResourceProperties('AWS::IAM::Role', {
      AssumeRolePolicyDocument: {
        Statement: [
          {
            Action: 'sts:AssumeRole',
            Effect: 'Allow',
            Principal: {
              Service: 'sagemaker.amazonaws.com',
            },
          },
        ],
      },
    });
  });

  test('HyperPod cluster is created', () => {
    template.hasResourceProperties('AWS::SageMaker::Cluster', {
      NodeRecovery: 'Automatic',
    });
  });

  test('Security group allows internal traffic', () => {
    template.hasResourceProperties('AWS::EC2::SecurityGroupIngress', {
      Description: 'Allow all traffic within security group',
      IpProtocol: '-1',
    });
  });

  test('VPC has S3 gateway endpoint', () => {
    template.hasResourceProperties('AWS::EC2::VPCEndpoint', {
      ServiceName: {
        'Fn::Join': [
          '',
          [
            'com.amazonaws.',
            { Ref: 'AWS::Region' },
            '.s3',
          ],
        ],
      },
      VpcEndpointType: 'Gateway',
    });
  });

  test('EKS node group is created', () => {
    template.hasResourceProperties('AWS::EKS::Nodegroup', {
      InstanceTypes: ['t3.small'],
      ScalingConfig: {
        DesiredSize: 1,
        MaxSize: 1,
        MinSize: 1,
      },
    });
  });

  test('CloudWatch log group is created for EKS', () => {
    template.hasResourceProperties('AWS::Logs::LogGroup', {
      LogGroupName: '/aws/eks/test-hyperpod-eks-cluster/cluster',
      RetentionInDays: 7,
    });
  });
});