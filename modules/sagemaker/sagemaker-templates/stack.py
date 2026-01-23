# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, List, Optional, Tuple, cast

import cdk_nag
from aws_cdk import BundlingOptions, BundlingOutput, DockerImage, Stack
from aws_cdk import aws_s3_assets as s3_assets
from constructs import Construct

from settings import ProjectTemplateType, RepositoryType
from templates.batch_inference.product_stack import BatchInferenceProject
from templates.finetune_llm_evaluation.product_stack import FinetuneLlmEvaluationProject
from templates.hf_import_models.product_stack import HfImportModelsProject
from templates.model_deploy.product_stack import ModelDeployProject
from templates.xgboost_abalone.product_stack import XGBoostAbaloneProject


class ProjectStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        project_template_type: ProjectTemplateType,
        sagemaker_domain_id: str,
        sagemaker_domain_arn: str,
        sagemaker_project_name: str,
        sagemaker_project_id: str,
        dev_vpc_id: str,
        dev_subnet_ids: List[str],
        dev_security_group_ids: List[str],
        pre_prod_account_id: str,
        pre_prod_region: str,
        pre_prod_vpc_id: str,
        pre_prod_subnet_ids: List[str],
        pre_prod_security_group_ids: List[str],
        prod_account_id: str,
        prod_region: str,
        prod_vpc_id: str,
        prod_subnet_ids: List[str],
        prod_security_group_ids: List[str],
        repository_type: RepositoryType,
        access_token_secret_name: Optional[str] = None,
        aws_codeconnection_arn: Optional[str] = None,
        repository_owner: Optional[str] = None,
        xgboost_abalone_project_settings: Any = None,
        model_deploy_project_settings: Any = None,
        hf_import_models_project_settings: Any = None,
        batch_inference_project_settings: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        build_app_asset, deploy_app_asset = self.upload_assets(
            template_name=project_template_type.value,
        )

        if project_template_type == ProjectTemplateType.XGBOOST_ABALONE:
            XGBoostAbaloneProject(
                self,
                "XGBoostAbaloneProject",
                build_app_asset=cast(s3_assets.Asset, build_app_asset),
                pre_prod_account_id=pre_prod_account_id,
                prod_account_id=prod_account_id,
                sagemaker_domain_id=sagemaker_domain_id,
                sagemaker_domain_arn=sagemaker_domain_arn,
                sagemaker_project_name=sagemaker_project_name,
                sagemaker_project_id=sagemaker_project_id,
                dev_vpc_id=dev_vpc_id,
                dev_subnet_ids=dev_subnet_ids,
                enable_network_isolation=xgboost_abalone_project_settings.enable_network_isolation,
                encrypt_inter_container_traffic=xgboost_abalone_project_settings.encrypt_inter_container_traffic,
                repository_type=repository_type,
                access_token_secret_name=access_token_secret_name,
                aws_codeconnection_arn=aws_codeconnection_arn,
                repository_owner=repository_owner,
            )
        elif project_template_type == ProjectTemplateType.BATCH_INFERENCE:
            BatchInferenceProject(
                self,
                "BatchInferenceProject",
                build_app_asset=cast(s3_assets.Asset, build_app_asset),
                sagemaker_project_name=sagemaker_project_name,
                sagemaker_project_id=sagemaker_project_id,
                sagemaker_domain_id=sagemaker_domain_id,
                sagemaker_domain_arn=sagemaker_domain_arn,
                model_package_group_name=batch_inference_project_settings.model_package_group_name,
                model_bucket_name=batch_inference_project_settings.model_bucket_name,
                base_job_prefix=batch_inference_project_settings.base_job_prefix,
                repository_type=repository_type,
                access_token_secret_name=access_token_secret_name,
                aws_codeconnection_arn=aws_codeconnection_arn,
                repository_owner=repository_owner,
            )
        elif project_template_type == ProjectTemplateType.FINETUNE_LLM_EVALUATION:
            FinetuneLlmEvaluationProject(
                self,
                "FinetuneLlmEvaluationProject",
                build_app_asset=cast(s3_assets.Asset, build_app_asset),
                sagemaker_project_name=sagemaker_project_name,
                sagemaker_project_id=sagemaker_project_id,
                pre_prod_account_id=pre_prod_account_id,
                prod_account_id=prod_account_id,
                sagemaker_domain_id=sagemaker_domain_id,
                sagemaker_domain_arn=sagemaker_domain_arn,
                repository_type=repository_type,
                access_token_secret_name=access_token_secret_name,
                aws_codeconnection_arn=aws_codeconnection_arn,
                repository_owner=repository_owner,
            )
        elif project_template_type == ProjectTemplateType.HF_IMPORT_MODELS:
            HfImportModelsProject(
                self,
                "HfImportModelsProject",
                build_app_asset=cast(s3_assets.Asset, build_app_asset),
                sagemaker_domain_id=sagemaker_domain_id,
                sagemaker_domain_arn=sagemaker_domain_arn,
                sagemaker_project_name=sagemaker_project_name,
                sagemaker_project_id=sagemaker_project_id,
                pre_prod_account_id=pre_prod_account_id,
                prod_account_id=prod_account_id,
                hf_access_token_secret=hf_import_models_project_settings.hf_access_token_secret,
                hf_model_id=hf_import_models_project_settings.hf_model_id,
                repository_type=repository_type,
                access_token_secret_name=access_token_secret_name,
                aws_codeconnection_arn=aws_codeconnection_arn,
                repository_owner=repository_owner,
            )
        elif project_template_type == ProjectTemplateType.MODEL_DEPLOY:
            ModelDeployProject(
                self,
                "ModelDeployProject",
                deploy_app_asset=cast(s3_assets.Asset, deploy_app_asset),
                sagemaker_project_name=sagemaker_project_name,
                sagemaker_project_id=sagemaker_project_id,
                model_package_group_name=model_deploy_project_settings.model_package_group_name,
                model_bucket_name=model_deploy_project_settings.model_bucket_name,
                enable_network_isolation=model_deploy_project_settings.enable_network_isolation,
                enable_manual_approval=model_deploy_project_settings.enable_manual_approval,
                enable_eventbridge_trigger=model_deploy_project_settings.enable_eventbridge_trigger,
                enable_data_capture=model_deploy_project_settings.enable_data_capture,
                dev_vpc_id=dev_vpc_id,
                dev_subnet_ids=dev_subnet_ids,
                dev_security_group_ids=dev_security_group_ids,
                pre_prod_account_id=pre_prod_account_id,
                pre_prod_region=pre_prod_region,
                pre_prod_vpc_id=pre_prod_vpc_id,
                pre_prod_subnet_ids=pre_prod_subnet_ids,
                pre_prod_security_group_ids=pre_prod_security_group_ids,
                prod_account_id=prod_account_id,
                prod_region=prod_region,
                prod_vpc_id=prod_vpc_id,
                prod_subnet_ids=prod_subnet_ids,
                prod_security_group_ids=prod_security_group_ids,
                sagemaker_domain_id=sagemaker_domain_id,
                sagemaker_domain_arn=sagemaker_domain_arn,
                repository_type=repository_type,
                access_token_secret_name=access_token_secret_name,
                aws_codeconnection_arn=aws_codeconnection_arn,
                repository_owner=repository_owner,
            )
        else:
            raise ValueError(f"Unsupported project template type: {project_template_type}")

    def upload_assets(
        self,
        template_name: str,
    ) -> Tuple[Optional[s3_assets.Asset], Optional[s3_assets.Asset]]:
        module_dir = os.path.dirname(os.path.abspath(__file__))
        zip_image = DockerImage.from_build(os.path.join(module_dir, "images/zip-image"))

        build_path = os.path.join(module_dir, f"templates/{template_name}/seed_code/build_app/")
        deploy_path = os.path.join(module_dir, f"templates/{template_name}/seed_code/deploy_app/")
        build_app_asset = None
        deploy_app_asset = None

        if os.path.isdir(build_path):
            build_app_asset = s3_assets.Asset(
                self,
                f"{template_name}BuildAsset",
                path=build_path,
                bundling=BundlingOptions(
                    image=zip_image,
                    command=[
                        "sh",
                        "-c",
                        """zip -r /asset-output/build_app.zip .""",
                    ],
                    output_type=BundlingOutput.ARCHIVED,
                ),
            )

        if os.path.isdir(deploy_path):
            deploy_app_asset = s3_assets.Asset(
                self,
                f"{template_name}DeployAsset",
                path=deploy_path,
                bundling=BundlingOptions(
                    image=zip_image,
                    command=[
                        "sh",
                        "-c",
                        """zip -r /asset-output/deploy_app.zip .""",
                    ],
                    output_type=BundlingOutput.ARCHIVED,
                ),
            )

            if build_app_asset:
                cdk_nag.NagSuppressions.add_resource_suppressions(
                    build_app_asset.bucket,
                    [
                        {
                            "id": "AwsSolutions-S1",
                            "reason": (
                                "S3 access logs are not required for CDK asset buckets as"
                                "they are managed by CDK and used for deployment artifacts only."
                            ),
                        }
                    ],
                )
            if deploy_app_asset:
                cdk_nag.NagSuppressions.add_resource_suppressions(
                    deploy_app_asset.bucket,
                    [
                        {
                            "id": "AwsSolutions-S1",
                            "reason": (
                                "S3 access logs are not required for CDK asset buckets as"
                                "they are managed by CDK and used for deployment artifacts only."
                            ),
                        }
                    ],
                )

        return build_app_asset, deploy_app_asset
