from typing import Any, Union
from aws_cdk import (
    Stack,
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam,
    CfnOutput,
    Duration,
    Fn,
)
from aws_cdk.aws_s3 import Bucket
import aws_cdk.aws_stepfunctions as sfn
import aws_cdk.aws_stepfunctions_tasks as tasks
from constructs import Construct

from lib.constructs.labeling_pipeline_assets import PipelineAssets


class ExecuteStateMachinePipeline(Stack):
    def __init__(
        self, scope: Construct, id: str, props: dict[str, Any], **kwargs: Any
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.props = props
        # Import the assets bucket
        data_bucket_name = Fn.import_value("aiopsDataBucket")

        # Deploy all assets required by the labeling pipeline
        pipeline_assets = PipelineAssets(self, "LabelingPipelineAssets", props)
        # Create the pipeline_role
        pipeline_role = pipeline_assets.create_execution_role(data_bucket_name, props)

        state_machine = sfn.StateMachine(
            self,
            "Labeling",
            definition=self.get_state_machine_definition(
                pipeline_assets, self.props, pipeline_role
            ),
            state_machine_name="Quality-Inspection-Labeling",
        )

        step_function_action = codepipeline_actions.StepFunctionInvokeAction(
            action_name="Invoke",
            state_machine=state_machine,
            state_machine_input=codepipeline_actions.StateMachineInput.literal({}),
        )

        labeling_execution_pipeline = codepipeline.Pipeline(
            self,
            "LabelingExecutionPipeline",
            artifact_bucket=Bucket.from_bucket_name(
                self, "artifactsbucket", data_bucket_name
            ),
            pipeline_name="aiopsEdge-Labeling-Pipeline",
            cross_account_keys=False,
            stages=[
                codepipeline.StageProps(
                    stage_name="Source", actions=[self.get_code_source(props)]
                ),
                codepipeline.StageProps(
                    stage_name="RunLabelingPipeline", actions=[step_function_action]
                ),
            ],
        )

        self.labeling_pipeline_name = CfnOutput(
            self,
            "LabelingPipelineNameExport",
            value=labeling_execution_pipeline.pipeline_name,
        )

    def get_code_source(
        self, props: dict[str, Any]
    ) -> Union[
        codepipeline_actions.CodeCommitSourceAction,
        codepipeline_actions.CodeStarConnectionsSourceAction,
    ]:
        source_output = codepipeline.Artifact()
        repo_type = props.get("repo_type", "")
        repo_name = props.get("repo_name", "")
        if repo_type == "CODECOMMIT" or repo_type == "CODECOMMIT_PROVIDED":
            repository = codecommit.Repository.from_repository_name(
                self, "repository", repo_name
            )
            return codepipeline_actions.CodeCommitSourceAction(
                action_name="CodeCommit",
                repository=repository,
                branch=props.get("branch_name"),
                output=source_output,
                trigger=codepipeline_actions.CodeCommitTrigger.NONE,
            )
        else:
            return codepipeline_actions.CodeStarConnectionsSourceAction(
                action_name=f"{props.get('github_repo_owner')}_{props.get('repo_name')}",
                branch=props.get("branch_name"),
                output=source_output,
                owner=props.get("github_repo_owner", ""),
                repo=props.get("repo_name", ""),
                connection_arn=props.get("github_connection_arn", ""),
                trigger_on_push=False,
            )

    def get_state_machine_definition(
        self,
        pipeline_assets: PipelineAssets,
        props: dict[str, Any],
        pipeline_role: iam.Role,
    ) -> sfn.Chain:
        success = sfn.Succeed(self, "Labeling Pipeline execution succeeded")
        fail = sfn.Fail(self, "Labeling Pipeline execution failed")
        check_missing_labels_lambda = pipeline_assets.check_missing_labels_lambda
        verification_job_lambda = pipeline_assets.verification_job_lambda
        labeling_job_lambda = pipeline_assets.labeling_job_lambda
        update_feature_store_lambda_function = (
            pipeline_assets.update_feature_store_lambda_function
        )
        check_missing_labels = tasks.LambdaInvoke(
            self, "CheckMissingLabels", lambda_function=check_missing_labels_lambda
        )
        # update_feature_store_lambda_function=pipeline_assets.update_feature_store_lambda(props, pipeline_role)

        update_feature_store = tasks.LambdaInvoke(
            self,
            "UpdateLabelsInFeatureStore",
            lambda_function=update_feature_store_lambda_function,
            payload=sfn.TaskInput.from_object(
                {
                    "executionId": sfn.JsonPath.string_at("$$.Execution.Id"),
                    "verification_job_output": sfn.JsonPath.string_at(
                        "$.LabelingJobOutput.OutputDatasetS3Uri"
                    ),
                }
            ),
        )

        run_labeling_job = tasks.LambdaInvoke(
            self,
            "StartLabelingJob",
            lambda_function=labeling_job_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "executionId": sfn.JsonPath.string_at("$$.Execution.Id"),
                    "request": sfn.JsonPath.entire_payload,
                }
            ),
            output_path="$.Payload",
        )

        run_verification_job = tasks.LambdaInvoke(
            self,
            "StartVerificationJob",
            lambda_function=verification_job_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "executionId": sfn.JsonPath.string_at("$$.Execution.Id"),
                    "input_manifest": sfn.JsonPath.string_at(
                        "$.LabelingJobOutput.OutputDatasetS3Uri"
                    ),
                }
            ),
            output_path="$.Payload",
        )

        # First, run the check_missing_labels lambda
        definition = check_missing_labels.next(
            sfn.Choice(self, "Missing Labels?")
            # If all images are labeled, end the pipeline
            .when(
                sfn.Condition.number_equals("$.Payload.missing_labels_count", 0),
                success,
            )
            .otherwise(
                run_labeling_job
                # Otherwise, run the labeling job
                .next(
                    self.create_labeling_job_waiter(
                        "LabelingJob",
                        fail,
                        run_verification_job
                        # Then run the verification job and update labels in the feature store
                        .next(
                            self.create_labeling_job_waiter(
                                "VerificationJob",
                                fail,
                                update_feature_store.next(success),
                            )
                        ),
                    )
                )
            )
        )

        return definition

    def create_labeling_job_waiter(
        self, labeling_job_name: str, fail: sfn.Fail, next: sfn.IChainable
    ) -> sfn.Chain:
        get_labeling_job_status = tasks.CallAwsService(
            self,
            f"Get {labeling_job_name} status",
            service="sagemaker",
            action="describeLabelingJob",
            parameters={"LabelingJobName": sfn.JsonPath.string_at("$.LabelingJobName")},
            iam_resources=["*"],
        )

        wait_x = sfn.Wait(
            self,
            f"Waiting for - {labeling_job_name} - completion",
            time=sfn.WaitTime.duration(Duration.seconds(30)),
        )

        return wait_x.next(get_labeling_job_status).next(
            sfn.Choice(self, f"{labeling_job_name} Complete?")
            .when(sfn.Condition.string_equals("$.LabelingJobStatus", "Failed"), fail)
            .when(sfn.Condition.string_equals("$.LabelingJobStatus", "Stopped"), fail)
            .when(sfn.Condition.string_equals("$.LabelingJobStatus", "Completed"), next)
            .otherwise(wait_x)
        )
