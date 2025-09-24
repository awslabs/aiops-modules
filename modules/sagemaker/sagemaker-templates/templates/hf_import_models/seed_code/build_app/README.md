# SageMaker Build - Train Pipelines

This folder contains all the SageMaker Pipelines of your project.

`buildspec.yml` defines how to run a pipeline after each commit to this repository.
`ml_pipelines/` contains the SageMaker pipelines definitions.
The expected output of your main pipeline (here `training/pipeline.py`) is a model registered to SageMaker Model Registry.

`tests/` contains the unittests for your `source_scripts/`

`notebooks/` contains experimentation notebooks.

