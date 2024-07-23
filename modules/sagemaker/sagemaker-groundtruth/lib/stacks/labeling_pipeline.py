from aws_cdk import (
    Stack,
    Stage,
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_iam as iam,
    aws_events as events,
    aws_s3 as s3,
    aws_events_targets as events_targets,
    pipelines,
    Fn,
)

from constructs import Construct

from stacks.statemachine_pipeline import (
    ExecuteStateMachinePipeline as StateMachinePipeline,
)


class LabelingPipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, props: dict, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Pass in our artifacts bucket instead of creating a new one
        data_bucket_name = Fn.import_value("aiopsDataBucket")
        labeling_pipeline = codepipeline.Pipeline(
            self,
            "LabelingPipeline",
            pipeline_name="aiopsEdge-Labeling-Infra-Pipeline",
            artifact_bucket=s3.Bucket.from_bucket_name(
                self, "aiops-bucket", data_bucket_name
            ),
            restart_execution_on_update=True,
        )

        pipeline = pipelines.CodePipeline(
            self,
            "cdk-pipeline",
            code_pipeline=labeling_pipeline,
            code_build_defaults={
                "build_environment": {"privileged": True},
                "role_policy": [
                    iam.PolicyStatement(
                        actions=["codepipeline:StartPipelineExecution"], resources=["*"]
                    )
                ],
            },
            synth=pipelines.ShellStep(
                "Synth",
                input=self.get_code_source(props),
                commands=[
                    "python -m venv .venv",
                    ". .venv/bin/activate",
                    "pip install -r requirements.txt",
                    "python app.py synth",
                ],
                primary_output_directory="labeling/cdk.out",
            ),
        )

        stage = DeployLabelingPipelineStage(self, "aiops-Labeling", props)

        trigger_step = pipelines.ShellStep(
            "InvokeLabelingPipeline",
            env_from_cfn_outputs={"PIPELINE_NAME": stage.pipeline_name},
            commands=[
                "aws codepipeline start-pipeline-execution --name $PIPELINE_NAME"
            ],
        )

        pipeline.add_stage(stage, post=[trigger_step])

        pipeline.build_pipeline()

        # Create scheduled trigger for labeling pipeline

        rule = events.Rule(
            self,
            "Rule",
            schedule=events.Schedule.expression(props.labeling_pipeline_schedule),
        )

        rule.add_target(events_targets.CodePipeline(pipeline.pipeline))

    def get_code_source(self, props: dict) -> pipelines.CodePipelineSource:
        repo_type = props.repo_type

        if repo_type == "CODECOMMIT" or repo_type == "CODECOMMIT_PROVIDED":
            repo = codecommit.Repository.from_repository_name(
                self, "ImportedRepo", props.repo_name
            )

            return pipelines.CodePipelineSource.code_commit(repo, props.branch_name)

        else:
            return pipelines.CodePipelineSource.connection(
                f"{props['github_repo_owner']}/{props.repo_name}",
                props.branch_name,
                connection_arn=props.github_connection_arn,
            )


class DeployLabelingPipelineStage(Stage):
    def __init__(self, scope: Construct, id: str, props: dict, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        labeling_pipeline_stack = StateMachinePipeline(
            self,
            "Statemachine-Pipeline-Stack",
            props=props,
            stack_name="LabelingPipelineStack",
        )

        self.pipeline_name = labeling_pipeline_stack.labeling_pipeline_name
