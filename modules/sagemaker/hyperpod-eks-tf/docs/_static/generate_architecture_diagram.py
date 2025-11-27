#!/usr/bin/env python3

from diagrams import Diagram, Cluster
from diagrams.aws.compute import EKS, EC2
from diagrams.aws.network import VPC, PrivateSubnet, PublicSubnet, InternetGateway, NATGateway, Endpoint
from diagrams.aws.security import IAMRole, IAM
from diagrams.aws.storage import S3, FSx
from diagrams.aws.ml import Sagemaker
from diagrams.k8s.compute import Pod

with Diagram("SageMaker HyperPod EKS Architecture", show=False, direction="TB"):
    
    # Internet Gateway
    igw = InternetGateway("Internet Gateway")
    
    with Cluster("VPC (10.192.0.0/16)"):
        
        with Cluster("Public Subnets"):
            pub_subnet_1 = PublicSubnet("Public Subnet 1\n(10.192.10.0/24)")
            pub_subnet_2 = PublicSubnet("Public Subnet 2\n(10.192.11.0/24)")
            nat_gw = NATGateway("NAT Gateway")
        
        with Cluster("Private Subnets"):
            private_subnet = PrivateSubnet("Private Subnet\n(10.1.0.0/16)")
            
            with Cluster("EKS Private Subnets"):
                eks_subnet_1 = PrivateSubnet("EKS Subnet 1\n(10.192.7.0/28)")
                eks_subnet_2 = PrivateSubnet("EKS Subnet 2\n(10.192.8.0/28)")
                eks_node_subnet = PrivateSubnet("EKS Node Subnet\n(10.192.9.0/24)")
        
        # Security Group
        sg = IAM("Security Group")
        
        # S3 VPC Endpoint
        s3_endpoint = Endpoint("S3 VPC Endpoint")
        
        with Cluster("EKS Cluster"):
            eks = EKS("EKS Cluster\n(Kubernetes 1.31)")
            
            with Cluster("Kubernetes Workloads"):
                helm_pods = Pod("HyperPod\nDependencies\n(Helm)")
                
        with Cluster("SageMaker HyperPod"):
            hyperpod = Sagemaker("HyperPod Cluster")
            
            with Cluster("Instance Groups"):
                instance_group = EC2("ml.trn1.32xlarge\nInstances")
        
        # FSx Lustre
        fsx = FSx("FSx Lustre\nHigh Performance\nStorage")
    
    # External Resources
    with Cluster("External AWS Services"):
        s3_bucket = S3("S3 Bucket\n(Lifecycle Scripts)")
        iam_role = IAMRole("SageMaker\nIAM Role")
    
    # Connections
    igw >> nat_gw
    nat_gw >> private_subnet
    
    # EKS connections
    eks >> helm_pods
    eks >> sg
    
    # HyperPod connections
    hyperpod >> instance_group
    hyperpod >> iam_role
    hyperpod >> fsx
    
    # Storage connections
    s3_endpoint >> s3_bucket
    instance_group >> fsx
    
    # Network flow
    private_subnet >> eks
    eks_subnet_1 >> eks
    eks_subnet_2 >> eks
    eks_node_subnet >> eks

print("Architecture diagram generated as 'sagemaker_hyperpod_eks_architecture.png'")
