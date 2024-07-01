from typing import Any

from aws_cdk import Aws
from aws_cdk import aws_iam as iam
from constructs import Construct


class Personas(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        app_prefix: str,
        bucket_name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id)

        # Define common permissions
        sagemaker_describe_permissions = [
            "sagemaker:DescribeModel",
            "sagemaker:DescribeEndpoint",
            "sagemaker:DescribeEndpointConfig",
            "sagemaker:DescribeTrainingJob",
            "sagemaker:DescribeHyperParameterTuningJob",
            "sagemaker:DescribeProcessingJob",
            "sagemaker:DescribeTransformJob",
        ]

        sagemaker_list_permissions = [
            "sagemaker:ListModels",
            "sagemaker:ListEndpoints",
            "sagemaker:ListEndpointConfigs",
            "sagemaker:ListTrainingJobs",
            "sagemaker:ListHyperParameterTuningJobs",
            "sagemaker:ListProcessingJobs",
            "sagemaker:ListTransformJobs",
        ]

        s3_permissions = [
            "s3:GetObject",
            "s3:ListBucket",
        ]

        ecr_permissions = [
            "ecr:GetAuthorizationToken",
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage",
        ]

        glue_describe_permissions = [
            "glue:GetTable",
            "glue:GetDatabase",
            "glue:GetJob",
            "glue:GetTrigger",
            "glue:GetCrawler",
            "glue:GetDevEndpoint",
        ]
        # ML Engineer role
        ml_engineer_role = iam.Role(
            self,
            "MLEngineerRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            role_name=f"{app_prefix}-MLEngineer",
            inline_policies={
                "MLEngineerPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sagemaker:CreateModel",
                                "sagemaker:CreateEndpoint",
                                "sagemaker:CreateEndpointConfig",
                                "sagemaker:CreateTrainingJob",
                                "sagemaker:CreateHyperParameterTuningJob",
                                "sagemaker:CreateProcessingJob",
                                "sagemaker:CreateTransformJob",
                                *sagemaker_describe_permissions,
                                *sagemaker_list_permissions,
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=s3_permissions,
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "codecommit:GitPull",
                                "codecommit:GitPush",
                                "codecommit:GetRepository",
                                "codecommit:CreateRepository",
                                "codecommit:DeleteRepository",
                                "codecommit:ListBranches",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["codepipeline:*", "codebuild:*"],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=ecr_permissions,
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["lambda:InvokeFunction"],
                            resources=["*"],
                        ),
                    ]
                )
            },
        )
        self.ml_engineer_role = ml_engineer_role
        # Data Engineers role
        data_engineer_role = iam.Role(
            self,
            "DataEngineerRole",
            role_name=f"{app_prefix}-DataEngineer",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("glue.amazonaws.com"),
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("elasticmapreduce.amazonaws.com"),
            ),
            inline_policies={
                "DataEngineerS3Policy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:PutObject",
                                "s3:DeleteObject",
                                *s3_permissions,
                            ],
                            resources=[f"arn:{Aws.PARTITION}:s3:::{bucket_name}/*"],
                        )
                    ]
                ),
                "DataEngineerGluePolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "glue:CreateTable",
                                "glue:DeleteTable",
                                "glue:CreateJob",
                                "glue:DeleteJob",
                                "glue:StartJobRun",
                                "glue:CreateTrigger",
                                "glue:DeleteTrigger",
                                "glue:CreateCrawler",
                                "glue:DeleteCrawler",
                                "glue:StartCrawler",
                                "glue:CreateDevEndpoint",
                                "glue:DeleteDevEndpoint",
                                *glue_describe_permissions,
                            ],
                            resources=["*"],
                        )
                    ]
                ),
                "DataEngineerSageMakerPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sagemaker:CreateModel",
                                "sagemaker:CreateEndpoint",
                                "sagemaker:CreateEndpointConfig",
                                "sagemaker:CreateTrainingJob",
                                "sagemaker:CreateHyperParameterTuningJob",
                                "sagemaker:CreateProcessingJob",
                                "sagemaker:CreateTransformJob",
                                *sagemaker_describe_permissions,
                                *sagemaker_list_permissions,
                            ],
                            resources=["*"],
                        )
                    ]
                ),
            },
        )
        self.data_engineer_role = data_engineer_role
        # IT Lead role
        self.it_lead_role = iam.Role(
            self, "ITLeadRole", role_name=f"{app_prefix}-ITLead", assumed_by=iam.AccountRootPrincipal()
        )
        it_lead_policy = iam.Policy(
            self,
            "ITLeadPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "iam:ListRolePolicies",
                        "iam:ListAttachedRolePolicies",
                        "iam:PassRole",
                        "iam:CreateRole",
                        "iam:DeleteRole",
                        "iam:AttachRolePolicy",
                        "iam:DetachRolePolicy",
                        "iam:PutRolePolicy",
                        "iam:DeleteRolePolicy",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:iam::{Aws.ACCOUNT_ID}:role/*",
                        f"arn:{Aws.PARTITION}:iam::{Aws.ACCOUNT_ID}:policy/*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudformation:CreateStack",
                        "cloudformation:UpdateStack",
                        "cloudformation:DeleteStack",
                        "cloudformation:DescribeStacks",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStackResources",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:cloudformation:{Aws.REGION}:{Aws.ACCOUNT_ID}:stack/*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudwatch:PutMetricData",
                        "cloudwatch:GetMetricData",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:cloudwatch:{Aws.REGION}:{Aws.ACCOUNT_ID}:log-group/*",
                        f"arn:{Aws.PARTITION}:cloudwatch:{Aws.REGION}:{Aws.ACCOUNT_ID}:metric-data/*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2:DescribeInstances",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:CreateSecurityGroup",
                        "ec2:DeleteSecurityGroup",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:RevokeSecurityGroupIngress",
                        "ec2:CreateNetworkInterface",
                        "ec2:DeleteNetworkInterface",
                        "ec2:AttachNetworkInterface",
                        "ec2:DetachNetworkInterface",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:{Aws.ACCOUNT_ID}:instance/*",
                        f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:{Aws.ACCOUNT_ID}:network-interface/*",
                        f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:{Aws.ACCOUNT_ID}:security-group/*",
                        f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:{Aws.ACCOUNT_ID}:subnet/*",
                        f"arn:{Aws.PARTITION}:ec2:{Aws.REGION}:{Aws.ACCOUNT_ID}:vpc/*",
                    ],
                ),
            ],
        )

        it_lead_policy.attach_to_role(self.it_lead_role)

        self.business_analyst_role = iam.Role(
            self,
            "BusinessAnalystRole",
            role_name=f"{app_prefix}-BusinessAnalyst",
            assumed_by=iam.AccountRootPrincipal(),
        )

        # business analyst role
        business_analyst_policy = iam.Policy(
            self,
            "BusinessAnalystPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "quicksight:CreateDashboard",
                        "quicksight:DescribeDashboard",
                        "quicksight:UpdateDashboard",
                        "quicksight:QueryData",
                        "quicksight:DescribeDataSet",
                        "quicksight:DescribeDataSource",
                    ],
                    resources=["*"],
                ),
            ],
        )

        business_analyst_policy.attach_to_role(self.business_analyst_role)
        # MLOps Engineer role
        self.mlops_engineer_role = iam.Role(
            self,
            "MLOpsEngineerRole",
            role_name=f"{app_prefix}-MLOpsEngineer",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
                iam.ServicePrincipal("glue.amazonaws.com"),
                iam.ServicePrincipal("codepipeline.amazonaws.com"),
                iam.ServicePrincipal("codebuild.amazonaws.com"),
            ),
        )

        mlops_engineer_policy = iam.Policy(
            self,
            "MLOpsEngineerPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "sagemaker:CreateModel",
                        "sagemaker:CreateEndpoint",
                        "sagemaker:CreateEndpointConfig",
                        "sagemaker:CreateTrainingJob",
                        "sagemaker:CreateHyperParameterTuningJob",
                        "sagemaker:CreateProcessingJob",
                        "sagemaker:CreateTransformJob",
                        "sagemaker:DescribeModel",
                        "sagemaker:DescribeEndpoint",
                        "sagemaker:DescribeEndpointConfig",
                        "sagemaker:DescribeTrainingJob",
                        "sagemaker:DescribeHyperParameterTuningJob",
                        "sagemaker:DescribeProcessingJob",
                        "sagemaker:DescribeTransformJob",
                        "sagemaker:ListModels",
                        "sagemaker:ListEndpoints",
                        "sagemaker:ListEndpointConfigs",
                        "sagemaker:ListTrainingJobs",
                        "sagemaker:ListHyperParameterTuningJobs",
                        "sagemaker:ListProcessingJobs",
                        "sagemaker:ListTransformJobs",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListBucket",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:s3:::{bucket_name}/*",
                        f"arn:{Aws.PARTITION}:s3:::{bucket_name}",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "glue:GetTable",
                        "glue:GetDatabase",
                        "glue:CreateTable",
                        "glue:DeleteTable",
                        "glue:GetJob",
                        "glue:CreateJob",
                        "glue:DeleteJob",
                        "glue:StartJobRun",
                        "glue:GetTrigger",
                        "glue:CreateTrigger",
                        "glue:DeleteTrigger",
                        "glue:GetCrawler",
                        "glue:CreateCrawler",
                        "glue:DeleteCrawler",
                        "glue:StartCrawler",
                        "glue:GetDevEndpoint",
                        "glue:CreateDevEndpoint",
                        "glue:DeleteDevEndpoint",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                        "ecr:PutImage",
                        "ecr:InitiateLayerUpload",
                        "ecr:UploadLayerPart",
                        "ecr:CompleteLayerUpload",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "codepipeline:*",
                        "codebuild:*",
                    ],
                    resources=["*"],
                ),
            ],
        )

        mlops_engineer_policy.attach_to_role(self.mlops_engineer_role)
        # IT Auditor role
        self.it_auditor_role = iam.Role(
            self,
            "ITAuditorRole",
            role_name=f"{app_prefix}-ITAuditor",
            assumed_by=iam.AccountRootPrincipal(),
        )

        it_auditor_policy = iam.Policy(
            self,
            "ITAuditorPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "iam:GetRole",
                        "iam:GetRolePolicy",
                        "iam:ListRolePolicies",
                        "iam:ListAttachedRolePolicies",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudformation:DescribeStacks",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStackResources",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudwatch:GetMetricData",
                        "cloudwatch:GetMetricStatistics",
                        "cloudwatch:ListMetrics",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                        "logs:GetLogEvents",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2:DescribeInstances",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "sagemaker:DescribeModel",
                        "sagemaker:DescribeEndpoint",
                        "sagemaker:DescribeEndpointConfig",
                        "sagemaker:DescribeTrainingJob",
                        "sagemaker:DescribeHyperParameterTuningJob",
                        "sagemaker:DescribeProcessingJob",
                        "sagemaker:DescribeTransformJob",
                        "sagemaker:ListModels",
                        "sagemaker:ListEndpoints",
                        "sagemaker:ListEndpointConfigs",
                        "sagemaker:ListTrainingJobs",
                        "sagemaker:ListHyperParameterTuningJobs",
                        "sagemaker:ListProcessingJobs",
                        "sagemaker:ListTransformJobs",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:ListBucket",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:s3:::{bucket_name}/*",
                        f"arn:{Aws.PARTITION}:s3:::{bucket_name}",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "glue:GetTable",
                        "glue:GetDatabase",
                        "glue:GetJob",
                        "glue:GetTrigger",
                        "glue:GetCrawler",
                        "glue:GetDevEndpoint",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                    ],
                    resources=["*"],
                ),
            ],
        )

        it_auditor_policy.attach_to_role(self.it_auditor_role)
        # Model Risk Manager role
        self.model_risk_manager_role = iam.Role(
            self,
            "ModelRiskManagerRole",
            role_name=f"{app_prefix}-ModelRiskManager",
            assumed_by=iam.AccountRootPrincipal(),
        )

        model_risk_manager_policy = iam.Policy(
            self,
            "ModelRiskManagerPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "sagemaker:DescribeModel",
                        "sagemaker:DescribeEndpoint",
                        "sagemaker:DescribeEndpointConfig",
                        "sagemaker:DescribeTrainingJob",
                        "sagemaker:DescribeHyperParameterTuningJob",
                        "sagemaker:DescribeProcessingJob",
                        "sagemaker:DescribeTransformJob",
                        "sagemaker:ListModels",
                        "sagemaker:ListEndpoints",
                        "sagemaker:ListEndpointConfigs",
                        "sagemaker:ListTrainingJobs",
                        "sagemaker:ListHyperParameterTuningJobs",
                        "sagemaker:ListProcessingJobs",
                        "sagemaker:ListTransformJobs",
                    ],
                    resources=[f"arn:{Aws.PARTITION}:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:model/*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:ListBucket",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:s3:::{bucket_name}/*",
                        f"arn:{Aws.PARTITION}:s3:::{bucket_name}",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "glue:GetTable",
                        "glue:GetDatabase",
                        "glue:GetJob",
                        "glue:GetTrigger",
                        "glue:GetCrawler",
                        "glue:GetDevEndpoint",
                    ],
                    resources=[
                        f"arn:{Aws.PARTITION}:glue:{Aws.REGION}:{Aws.ACCOUNT_ID}:crawler/*",
                        f"arn:{Aws.PARTITION}:glue:{Aws.REGION}:{Aws.ACCOUNT_ID}:job/*"
                        f"arn:{Aws.PARTITION}:glue:{Aws.REGION}:{Aws.ACCOUNT_ID}:catalog/*",
                        f"arn:{Aws.PARTITION}:glue:{Aws.REGION}:{Aws.ACCOUNT_ID}:database/*",
                        f"arn:{Aws.PARTITION}:glue:{Aws.REGION}:{Aws.ACCOUNT_ID}:table/*",
                        f"arn:{Aws.PARTITION}:glue:{Aws.REGION}:{Aws.ACCOUNT_ID}:devEndpoint/*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                    ],
                    resources=[f"arn:{Aws.PARTITION}:ecr:{Aws.REGION}:{Aws.ACCOUNT_ID}:repository/*"],
                ),
            ],
        )

        model_risk_manager_policy.attach_to_role(self.model_risk_manager_role)
