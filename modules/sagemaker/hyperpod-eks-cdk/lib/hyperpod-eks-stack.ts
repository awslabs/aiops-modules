import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as eks from 'aws-cdk-lib/aws-eks';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as cr from 'aws-cdk-lib/custom-resources';
import { KubectlV32Layer } from '@aws-cdk/lambda-layer-kubectl-v32';
import { Construct } from 'constructs';
import { NagSuppressions } from 'cdk-nag';

export interface HyperpodEksStackProps extends cdk.StackProps {
  readonly resourceNamePrefix?: string;
  readonly vpcCidr?: string;
  readonly kubernetesVersion?: eks.KubernetesVersion;
  readonly instanceGroups?: { [key: string]: InstanceGroupConfig };
}

export interface InstanceGroupConfig {
  readonly instanceType: string;
  readonly instanceCount: number;
  readonly ebsVolumeSize: number;
  readonly threadsPerCore: number;
  readonly enableStressCheck: boolean;
  readonly enableConnectivityCheck: boolean;
  readonly lifecycleScript: string;
}

export class HyperpodEksStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly eksCluster: eks.Cluster;
  public readonly s3Bucket: s3.Bucket;
  public readonly sagemakerRole: iam.Role;

  constructor(scope: Construct, id: string, props: HyperpodEksStackProps = {}) {
    super(scope, id, props);

    const resourceNamePrefix = props.resourceNamePrefix || 'sagemaker-hyperpod-eks';
    const vpcCidr = props.vpcCidr || '10.192.0.0/16';
    const kubernetesVersion = props.kubernetesVersion || eks.KubernetesVersion.V1_31;

    // Create VPC with public and private subnets
    this.vpc = this.createVpc(resourceNamePrefix, vpcCidr);

    // Create S3 bucket for lifecycle scripts and data
    this.s3Bucket = this.createS3Bucket(resourceNamePrefix);

    // Create SageMaker execution role
    this.sagemakerRole = this.createSageMakerRole(resourceNamePrefix);

    // Create EKS cluster
    this.eksCluster = this.createEksCluster(resourceNamePrefix, kubernetesVersion);

    // Deploy lifecycle script to S3
    this.deployLifecycleScript();

    // Install HyperPod Helm chart dependencies
    const helmInstallation = this.installHyperPodHelmChart();

    // Create HyperPod cluster (depends on Helm chart installation)
    this.createHyperPodCluster(resourceNamePrefix, props.instanceGroups, helmInstallation);

    // Add CDK Nag suppressions for known acceptable cases
    this.addNagSuppressions();
  }

  private createVpc(resourceNamePrefix: string, vpcCidr: string): ec2.Vpc {
    const vpc = new ec2.Vpc(this, 'HyperpodVpc', {
      ipAddresses: ec2.IpAddresses.cidr(vpcCidr),
      maxAzs: 2,
      enableDnsHostnames: true,
      enableDnsSupport: true,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
      ],
    });

    // Add VPC endpoint for S3
    vpc.addGatewayEndpoint('S3Endpoint', {
      service: ec2.GatewayVpcEndpointAwsService.S3,
      subnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
    });

    // Tag subnets for EKS
    vpc.privateSubnets.forEach((subnet) => {
      cdk.Tags.of(subnet).add('kubernetes.io/role/internal-elb', '1');
      cdk.Tags.of(subnet).add(`kubernetes.io/cluster/${resourceNamePrefix}-cluster`, 'shared');
    });

    vpc.publicSubnets.forEach((subnet) => {
      cdk.Tags.of(subnet).add('kubernetes.io/role/elb', '1');
      cdk.Tags.of(subnet).add(`kubernetes.io/cluster/${resourceNamePrefix}-cluster`, 'shared');
    });

    return vpc;
  }

  private createS3Bucket(resourceNamePrefix: string): s3.Bucket {
    const bucket = new s3.Bucket(this, 'HyperpodS3Bucket', {
      bucketName: `${resourceNamePrefix}-bucket-${this.account}-${this.region}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For demo purposes
      autoDeleteObjects: true, // For demo purposes
    });

    return bucket;
  }

  private createSageMakerRole(resourceNamePrefix: string): iam.Role {
    const role = new iam.Role(this, 'SageMakerExecutionRole', {
      roleName: `${resourceNamePrefix}-SMHP-Exec-Role-${this.region}`,
      assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerClusterInstanceRolePolicy'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKS_CNI_Policy'),
      ],
    });

    // Add custom policy for EC2, ECR, and S3 permissions
    role.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'ec2:AssignPrivateIpAddresses',
        'ec2:CreateNetworkInterface',
        'ec2:CreateNetworkInterfacePermission',
        'ec2:DeleteNetworkInterface',
        'ec2:DeleteNetworkInterfacePermission',
        'ec2:DescribeNetworkInterfaces',
        'ec2:DescribeVpcs',
        'ec2:DescribeDhcpOptions',
        'ec2:DescribeSubnets',
        'ec2:DescribeSecurityGroups',
        'ec2:DetachNetworkInterface',
        'ec2:ModifyNetworkInterfaceAttribute',
        'ec2:UnassignPrivateIpAddresses',
        'ecr:BatchGetImage',
        'ecr:GetAuthorizationToken',
        'ecr:GetDownloadUrlForLayer',
        'eks-auth:AssumeRoleForPodIdentity',
        'cloudwatch:DescribeAlarms',
      ],
      resources: ['*'],
    }));

    role.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['ec2:CreateTags'],
      resources: ['arn:aws:ec2:*:*:network-interface/*'],
    }));

    role.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['s3:ListBucket', 's3:GetObject'],
      resources: [
        this.s3Bucket.bucketArn,
        `${this.s3Bucket.bucketArn}/*`,
      ],
    }));

    return role;
  }

  private createEksCluster(resourceNamePrefix: string, kubernetesVersion: eks.KubernetesVersion): eks.Cluster {
    // Create security group for EKS
    const eksSecurityGroup = new ec2.SecurityGroup(this, 'EksSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for EKS cluster',
      allowAllOutbound: true,
    });

    // Allow all traffic within the security group
    eksSecurityGroup.addIngressRule(
      eksSecurityGroup,
      ec2.Port.allTraffic(),
      'Allow all traffic within security group'
    );

    // Create CloudWatch log group for EKS
    new logs.LogGroup(this, 'EksClusterLogGroup', {
      logGroupName: `/aws/eks/${resourceNamePrefix}-cluster/cluster`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const cluster = new eks.Cluster(this, 'EksCluster', {
      clusterName: `${resourceNamePrefix}-cluster`,
      version: kubernetesVersion,
      vpc: this.vpc,
      vpcSubnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
      securityGroup: eksSecurityGroup,
      endpointAccess: eks.EndpointAccess.PUBLIC_AND_PRIVATE,
      clusterLogging: [
        eks.ClusterLoggingTypes.API,
        eks.ClusterLoggingTypes.AUDIT,
        eks.ClusterLoggingTypes.AUTHENTICATOR,
        eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
        eks.ClusterLoggingTypes.SCHEDULER,
      ],
      authenticationMode: eks.AuthenticationMode.API_AND_CONFIG_MAP,
      kubectlLayer: new KubectlV32Layer(this, 'KubectlLayer'),
    });

    // Add managed node group
    cluster.addNodegroupCapacity('DefaultNodeGroup', {
      instanceTypes: [ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.SMALL)],
      minSize: 1,
      maxSize: 1,
      desiredSize: 1,
      subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
    });

    // Install essential add-ons using the newer Addon construct
    new eks.Addon(this, 'VpcCniAddon', {
      cluster: cluster,
      addonName: 'vpc-cni',
    });

    new eks.Addon(this, 'KubeProxyAddon', {
      cluster: cluster,
      addonName: 'kube-proxy',
    });

    new eks.Addon(this, 'CoreDnsAddon', {
      cluster: cluster,
      addonName: 'coredns',
    });

    new eks.Addon(this, 'PodIdentityAddon', {
      cluster: cluster,
      addonName: 'eks-pod-identity-agent',
    });

    return cluster;
  }

  private createHyperPodCluster(resourceNamePrefix: string, instanceGroups?: { [key: string]: InstanceGroupConfig }, helmInstallation?: cdk.CustomResource) {
    const defaultInstanceGroups = instanceGroups || {
      'instance-group-1': {
        instanceType: 'ml.g5.8xlarge',
        instanceCount: 8,
        ebsVolumeSize: 100,
        threadsPerCore: 2,
        enableStressCheck: true,
        enableConnectivityCheck: true,
        lifecycleScript: 'on_create.sh',
      },
    };

    // Create instance groups configuration
    const instanceGroupsConfig = Object.entries(defaultInstanceGroups).map(([name, config]) => {
      const healthChecks: string[] = [];
      if (config.enableStressCheck) healthChecks.push('InstanceStress');
      if (config.enableConnectivityCheck) healthChecks.push('InstanceConnectivity');

      return {
        InstanceGroupName: name,
        InstanceType: config.instanceType,
        InstanceCount: config.instanceCount,
        ThreadsPerCore: config.threadsPerCore,
        ExecutionRole: this.sagemakerRole.roleArn,
        InstanceStorageConfigs: [{
          EbsVolumeConfig: {
            VolumeSizeInGb: config.ebsVolumeSize,
          },
        }],
        LifeCycleConfig: {
          OnCreate: config.lifecycleScript,
          SourceS3Uri: `s3://${this.s3Bucket.bucketName}`,
        },
        ...(healthChecks.length > 0 && { OnStartDeepHealthChecks: healthChecks }),
      };
    });

    // Create HyperPod cluster using CloudFormation resource
    const hyperPodCluster = new cdk.CfnResource(this, 'HyperPodCluster', {
      type: 'AWS::SageMaker::Cluster',
      properties: {
        ClusterName: `${resourceNamePrefix}-ml-cluster`,
        InstanceGroups: instanceGroupsConfig,
        NodeRecovery: 'Automatic',
        Orchestrator: {
          Eks: {
            ClusterArn: this.eksCluster.clusterArn,
          },
        },
        VpcConfig: {
          SecurityGroupIds: [this.eksCluster.clusterSecurityGroup.securityGroupId],
          Subnets: this.vpc.privateSubnets.map(subnet => subnet.subnetId),
        },
      },
    });

    // Ensure HyperPod cluster depends on Helm installation (matching Terraform dependencies)
    if (helmInstallation) {
      hyperPodCluster.node.addDependency(helmInstallation);
    }
  }

  private deployLifecycleScript() {
    // Download and deploy the lifecycle script to S3
    // This replicates the Terraform http data source + s3_object resource
    const lifecycleScriptUrl = 'https://raw.githubusercontent.com/aws-samples/awsome-distributed-training/main/1.architectures/7.sagemaker-hyperpod-eks/LifecycleScripts/base-config/on_create.sh';

    // Create a custom resource to download and upload the script
    const downloadScriptProvider = new cr.Provider(this, 'DownloadScriptProvider', {
      onEventHandler: new lambda.Function(this, 'DownloadScriptHandler', {
        runtime: lambda.Runtime.PYTHON_3_12,
        handler: 'index.handler',
        code: lambda.Code.fromInline(`
import json
import urllib.request
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(f"Event: {json.dumps(event)}")
    
    request_type = event['RequestType']
    
    if request_type == 'Create' or request_type == 'Update':
        try:
            # Download the script
            script_url = event['ResourceProperties']['ScriptUrl']
            bucket_name = event['ResourceProperties']['BucketName']
            key = event['ResourceProperties']['Key']
            
            logger.info(f"Downloading script from {script_url}")
            with urllib.request.urlopen(script_url) as response:
                script_content = response.read()
            
            # Upload to S3
            s3_client = boto3.client('s3')
            s3_client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=script_content,
                ContentType='text/x-sh'
            )
            
            logger.info(f"Successfully uploaded script to s3://{bucket_name}/{key}")
            
            return {
                'Status': 'SUCCESS',
                'PhysicalResourceId': f"{bucket_name}/{key}",
                'Data': {
                    'ScriptUrl': f"s3://{bucket_name}/{key}"
                }
            }
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return {
                'Status': 'FAILED',
                'Reason': str(e),
                'PhysicalResourceId': 'failed'
            }
    
    elif request_type == 'Delete':
        # Clean up the S3 object
        try:
            bucket_name = event['ResourceProperties']['BucketName']
            key = event['ResourceProperties']['Key']
            
            s3_client = boto3.client('s3')
            s3_client.delete_object(Bucket=bucket_name, Key=key)
            
            return {
                'Status': 'SUCCESS',
                'PhysicalResourceId': event['PhysicalResourceId']
            }
        except Exception as e:
            logger.error(f"Error during delete: {str(e)}")
            return {
                'Status': 'SUCCESS',  # Don't fail stack deletion
                'PhysicalResourceId': event['PhysicalResourceId']
            }
`),
        timeout: cdk.Duration.minutes(5),
      }),
    });

    // Grant the Lambda function permissions to write to S3
    this.s3Bucket.grantWrite(downloadScriptProvider.onEventHandler);

    // Create the custom resource
    new cdk.CustomResource(this, 'LifecycleScriptDeployment', {
      serviceToken: downloadScriptProvider.serviceToken,
      properties: {
        ScriptUrl: lifecycleScriptUrl,
        BucketName: this.s3Bucket.bucketName,
        Key: 'on_create.sh',
      },
    });
  }

  private installHyperPodHelmChart() {
    // Install HyperPod Helm chart dependencies
    // This replicates the Terraform helm_release resource
    const helmChartManifest = this.eksCluster.addManifest('HyperPodHelmChart', {
      apiVersion: 'v1',
      kind: 'Namespace',
      metadata: {
        name: 'hyperpod-system',
        labels: {
          'app.kubernetes.io/name': 'hyperpod-system',
          'app.kubernetes.io/managed-by': 'cdk',
        },
      },
    });

    // Create a custom resource to install the Helm chart
    const helmInstallProvider = new cr.Provider(this, 'HelmInstallProvider', {
      onEventHandler: new lambda.Function(this, 'HelmInstallHandler', {
        runtime: lambda.Runtime.PYTHON_3_12,
        handler: 'index.handler',
        timeout: cdk.Duration.minutes(15),
        memorySize: 1024, // Increase memory for git operations
        code: lambda.Code.fromInline(`
import json
import subprocess
import tempfile
import os
import logging
import boto3
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def run_command(cmd, cwd=None, check=True):
    """Run command with proper logging and error handling"""
    logger.info(f"Running command: {' '.join(cmd)} in {cwd or 'current directory'}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    
    if result.stdout:
        logger.info(f"STDOUT: {result.stdout}")
    if result.stderr:
        logger.info(f"STDERR: {result.stderr}")
    
    if check and result.returncode != 0:
        logger.error(f"Command failed with return code {result.returncode}")
        raise Exception(f"Command failed: {result.stderr}")
    
    return result

def handler(event, context):
    logger.info(f"Event: {json.dumps(event)}")
    
    request_type = event['RequestType']
    
    if request_type == 'Create' or request_type == 'Update':
        try:
            cluster_name = event['ResourceProperties']['ClusterName']
            region = event['ResourceProperties']['Region']
            helm_repo_url = event['ResourceProperties']['HelmRepoUrl']
            helm_repo_path = event['ResourceProperties']['HelmRepoPath']
            namespace = event['ResourceProperties']['Namespace']
            release_name = event['ResourceProperties']['ReleaseName']
            
            logger.info("Starting git clone operation...")
            
            # Step 1: Git clone (replicating null_resource.git_clone)
            temp_dir = "/tmp/helm-repo"
            
            # Clean up existing directory
            logger.info("Cleaning up existing directory...")
            run_command(['rm', '-rf', temp_dir], check=False)
            
            # Create fresh directory
            logger.info("Creating fresh directory...")
            run_command(['mkdir', '-p', temp_dir])
            
            # Clone from repository
            logger.info(f"Cloning from {helm_repo_url}...")
            run_command(['git', 'clone', helm_repo_url, temp_dir])
            
            # List contents
            logger.info("Contents of /tmp/helm-repo:")
            result = run_command(['ls', '-la', temp_dir])
            logger.info(result.stdout)
            
            logger.info("Git clone complete")
            
            # Step 2: Helm dependency update (replicating null_resource.helm_dep_update)
            chart_path = os.path.join(temp_dir, helm_repo_path)
            
            logger.info("Starting helm dependency update...")
            
            if not os.path.exists(temp_dir):
                raise Exception("Error: /tmp/helm-repo directory does not exist")
            
            if not os.path.exists(chart_path):
                logger.error(f"Error: Chart directory {helm_repo_path} not found")
                result = run_command(['ls', '-la', temp_dir])
                logger.error(f"Contents of /tmp/helm-repo: {result.stdout}")
                raise Exception(f"Chart directory {helm_repo_path} not found")
            
            # Create charts directory if it doesn't exist
            charts_dir = os.path.join(chart_path, 'charts')
            logger.info("Creating charts directory if it doesn't exist...")
            run_command(['mkdir', '-p', charts_dir])
            
            # Parse Chart.yaml for dependencies and create empty Chart.yaml files if needed
            # This replicates the complex bash logic in Terraform
            chart_yaml_path = os.path.join(chart_path, 'Chart.yaml')
            if os.path.exists(chart_yaml_path):
                with open(chart_yaml_path, 'r') as f:
                    chart_content = f.read()
                
                # Extract dependency names (simplified version of the bash grep logic)
                import re
                dep_names = re.findall(r'name:\\s*([a-zA-Z0-9_-]+)', chart_content)
                
                for dep in dep_names:
                    dep_dir = os.path.join(charts_dir, dep)
                    if not os.path.exists(dep_dir):
                        logger.info(f"Creating directory for dependency: {dep}")
                        run_command(['mkdir', '-p', dep_dir])
                        
                        # Create empty Chart.yaml
                        empty_chart = f"apiVersion: v2\\nname: {dep}\\nversion: 0.1.0"
                        with open(os.path.join(dep_dir, 'Chart.yaml'), 'w') as f:
                            f.write(empty_chart.replace('\\\\n', '\\n'))
            
            # Run helm dependency update
            logger.info("Running helm dependency update...")
            run_command(['helm', 'dependency', 'update'], cwd=chart_path, check=False)
            logger.info("Helm dependency update complete")
            
            # Step 3: Update kubeconfig and install helm chart
            logger.info("Updating kubeconfig...")
            run_command(['aws', 'eks', 'update-kubeconfig', '--region', region, '--name', cluster_name])
            
            # Step 4: Install helm chart (replicating helm_release resource)
            logger.info(f"Installing helm chart {release_name}...")
            helm_cmd = [
                'helm', 'upgrade', '--install',
                release_name, chart_path,
                '--namespace', namespace,
                '--create-namespace',
                '--skip-crds',  # This matches skip_crds = true in Terraform
                '--dependency-update',  # This matches dependency_update = true in Terraform
                '--wait',
                '--timeout', '10m'
            ]
            
            run_command(helm_cmd)
            logger.info(f"Successfully installed Helm chart {release_name}")
            
            return {
                'Status': 'SUCCESS',
                'PhysicalResourceId': f"{cluster_name}-{release_name}",
                'Data': {
                    'ReleaseName': release_name,
                    'Namespace': namespace
                }
            }
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return {
                'Status': 'FAILED',
                'Reason': str(e),
                'PhysicalResourceId': 'failed'
            }
    
    elif request_type == 'Delete':
        try:
            cluster_name = event['ResourceProperties']['ClusterName']
            region = event['ResourceProperties']['Region']
            namespace = event['ResourceProperties']['Namespace']
            release_name = event['ResourceProperties']['ReleaseName']
            
            logger.info(f"Uninstalling helm chart {release_name}...")
            
            # Update kubeconfig
            run_command(['aws', 'eks', 'update-kubeconfig', '--region', region, '--name', cluster_name])
            
            # Uninstall the helm chart
            try:
                run_command(['helm', 'uninstall', release_name, '--namespace', namespace])
                logger.info(f"Successfully uninstalled helm chart {release_name}")
            except Exception as e:
                logger.warning(f"Helm uninstall failed, continuing: {e}")
            
            # Clean up the cloned repository
            run_command(['rm', '-rf', '/tmp/helm-repo'], check=False)
            
            return {
                'Status': 'SUCCESS',
                'PhysicalResourceId': event['PhysicalResourceId']
            }
            
        except Exception as e:
            logger.error(f"Error during delete: {str(e)}")
            return {
                'Status': 'SUCCESS',  # Don't fail stack deletion
                'PhysicalResourceId': event['PhysicalResourceId']
            }
`),

      }),
    });

    // Grant the Lambda function permissions to access EKS
    helmInstallProvider.onEventHandler.role?.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonEKSClusterPolicy')
    );

    // Add permissions to describe EKS cluster
    helmInstallProvider.onEventHandler.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'eks:DescribeCluster',
        'eks:ListClusters',
      ],
      resources: [this.eksCluster.clusterArn],
    }));

    // Create the custom resource with dependency on EKS cluster
    const helmInstallation = new cdk.CustomResource(this, 'HyperPodHelmInstallation', {
      serviceToken: helmInstallProvider.serviceToken,
      properties: {
        ClusterName: this.eksCluster.clusterName,
        Region: this.region,
        HelmRepoUrl: 'https://github.com/aws/sagemaker-hyperpod-cli.git',
        HelmRepoPath: 'helm_chart/HyperPodHelmChart',
        Namespace: 'kube-system',
        ReleaseName: 'hyperpod-dependencies',
      },
    });

    // Ensure Helm installation depends on the cluster being ready
    helmInstallation.node.addDependency(this.eksCluster);
    helmInstallation.node.addDependency(helmChartManifest);

    return helmInstallation;
  }

  private addNagSuppressions() {
    // Suppress CDK Nag warnings for acceptable cases
    NagSuppressions.addStackSuppressions(this, [
      {
        id: 'AwsSolutions-IAM4',
        reason: 'AWS managed policies are required for SageMaker and EKS functionality',
      },
      {
        id: 'AwsSolutions-IAM5',
        reason: 'Wildcard permissions are required for EKS and SageMaker cluster operations',
        appliesTo: [
          'Resource::*',
          'Resource::<OnEventHandler42BEBAE0.Arn>:*',
          'Resource::<IsCompleteHandler7073F4DA.Arn>:*',
          'Resource::<Handler886CB40B.Arn>:*',
          'Resource::<ProviderframeworkisComplete26D7B0CB.Arn>:*',
          'Resource::<ProviderframeworkonTimeout0B47CA38.Arn>:*',
          'Resource::arn:aws:ec2:*:*:network-interface/*',
          'Resource::<HyperpodS3Bucket522C1DD7.Arn>/*',
          'Resource::arn:aws:eks:us-east-1:<AWS::AccountId>:cluster/sagemaker-hyperpod-eks-cluster/*',
          'Resource::arn:aws:eks:us-east-1:<AWS::AccountId>:fargateprofile/sagemaker-hyperpod-eks-cluster/*',
        ],
      },
      {
        id: 'AwsSolutions-VPC7',
        reason: 'VPC Flow Logs not required for this demo environment',
      },
      {
        id: 'AwsSolutions-S1',
        reason: 'S3 access logging not required for this demo bucket',
      },
      {
        id: 'AwsSolutions-SF1',
        reason: 'Step Function logging not required for EKS cluster provider',
      },
      {
        id: 'AwsSolutions-SF2',
        reason: 'X-Ray tracing not required for EKS cluster provider',
      },
      {
        id: 'AwsSolutions-L1',
        reason: 'Lambda runtime version is managed by CDK for kubectl provider',
      },
      {
        id: 'AwsSolutions-EKS1',
        reason: 'Public endpoint access is required for cluster management and HyperPod integration',
      },
    ]);
  }
}