#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { HyperpodEksStack } from '../lib/hyperpod-eks-stack';
import { AwsSolutionsChecks } from 'cdk-nag';
import { defaultConfig } from '../config/default';

const app = new cdk.App();

// Apply CDK Nag for security and operational excellence validation
// Uncomment the line below to enable CDK Nag validation
// cdk.Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));

new HyperpodEksStack(app, 'HyperpodEksStack', {
  ...defaultConfig,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  description: 'SageMaker HyperPod with EKS infrastructure stack',
});