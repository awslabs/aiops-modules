import * as eks from 'aws-cdk-lib/aws-eks';
import { InstanceGroupConfig } from '../lib/hyperpod-eks-stack';

export interface HyperpodEksConfig {
  readonly resourceNamePrefix: string;
  readonly vpcCidr: string;
  readonly kubernetesVersion: eks.KubernetesVersion;
  readonly instanceGroups: { [key: string]: InstanceGroupConfig };
}

export const defaultConfig: HyperpodEksConfig = {
  resourceNamePrefix: 'hyper-test',
  vpcCidr: '10.192.0.0/16',
  kubernetesVersion: eks.KubernetesVersion.V1_32,
  instanceGroups: {
    'instance-group-1': {
      instanceType: 'ml.g5.8xlarge',
      instanceCount: 8,
      ebsVolumeSize: 100,
      threadsPerCore: 2,
      enableStressCheck: true,
      enableConnectivityCheck: true,
      lifecycleScript: 'on_create.sh',
    },
  },
};