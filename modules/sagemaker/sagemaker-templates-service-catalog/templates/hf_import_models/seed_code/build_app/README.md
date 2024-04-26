# SageMaker Build - Train Pipelines

This folder contains all the SageMaker Pipelines of your project.

`buildspec.yml` defines how to run a pipeline after each commit to this repository.
`ml_pipelines/` contains the SageMaker pipelines definitions.
The expected output of the your main pipeline (here `training/pipeline.py`) is a model registered to SageMaker Model Registry.

`tests/` contains the unittests for your `source_scripts/`

`notebooks/` contains experimentation notebooks.

# Run pipeline from command line from this folder

```
pip install -e .

run-pipeline --module-name ml_pipelines.training.pipeline --role-arn YOUR_SAGEMAKER_EXECUTION_ROLE_ARN --kwargs '{"region":"eu-west-1"}'
```
