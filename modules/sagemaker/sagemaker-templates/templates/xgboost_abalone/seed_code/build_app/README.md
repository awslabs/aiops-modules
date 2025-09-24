# SageMaker Build - Train Pipelines

This folder contains all the SageMaker Pipelines of your project.

`buildspec.yml` defines how to run a pipeline after each commit to this repository.
`ml_pipelines/` contains the SageMaker pipelines definitions.
The expected output of the main pipeline (from `training/pipeline.py`) is a model registered to SageMaker Model Registry.

`source_scripts/` contains the underlying scripts run by the steps of your SageMaker Pipelines. For example, if your SageMaker Pipeline runs a Processing Job as part of a Processing Step, the code being run inside the Processing Job should be defined in this folder.
Typically `source_scripts/` can contain individual scripts `preprocessing.py`, `training.py`, `postprocessing.py`, `evaluate.py`, depending on the nature of the steps run as part of the SageMaker Pipeline.
We provide here an example with the Abalone dataset, to train an XGBoost model (using), and evaluating the model on a test set before sending it for manual approval to SageMaker Model Registry inside the SageMaker ModelPackageGroup defined when creating the SageMaker Project.
Additionally, if you use custom containers, the Dockerfile definitions should be found in that folder.

`notebooks/` contains experimentation notebooks.

# Run pipeline from command line from this folder

```
pip install -e .

run-pipeline --module-name ml_pipelines.training.pipeline --role-arn YOUR_SAGEMAKER_EXECUTION_ROLE_ARN --kwargs '{"region":"eu-west-1"}'
```
