# SageMaker Ground truth labeling examples

### Description

This folder contains examples for each of the built-in task types for the sagemaker ground truth module. Each folder contains an example manifest as well as any necessary templates. Please upload the templates to an S3 bucket and update the manifest with the correct location.

### Additional workers

For tasks without a verification step (all except `image_bounding_box` and `image_semantic_segmentation`) we recommend increasing the number of human reviewers per object to increase accuracy. This will only work if you have at least that many reviewers in your workteam, as the same reviewer cannot review the same item twice. To adjust the number of workers add the additional parameters below to your manifest:

```yaml
  - name: labeling-human-task-config
    value:
      NumberOfHumanWorkersPerDataObject: 5
      TaskAvailabilityLifetimeInSeconds: 21600
      TaskTimeLimitInSeconds: 300
```

### Using public workforce

As mentioned in the README you can use a public workforce for your task if you wish (at an additional cost). More information on using a public workforce like Amazon Mechanical Turk is available [here](https://docs.aws.amazon.com/sagemaker/latest/dg/sms-workforce-management-public.html). Labeling and verification task prices is specified in USD, see [here](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_PublicWorkforceTaskPrice.html) for allowed values. [This page](https://aws.amazon.com/sagemaker/groundtruth/pricing/) provides suggested pricing based on task type. To use a public workforce add / adjust the following parameters to your manifest:

```yaml
  - name: labeling-workteam-arn
    value: 'arn:aws:sagemaker:<region>:394669845002:workteam/public-crowd/default'
  - name: labeling-task-price
    value:
      AmountInUsd:
        Dollars: 0
        Cents: 3
        TenthFractionsOfACent: 6
  - name: verification-workteam-arn
    value: 'arn:aws:sagemaker:<region>:394669845002:workteam/public-crowd/default'
  - name: verification-task-price
    value:
      AmountInUsd:
        Dollars: 0
        Cents: 3
        TenthFractionsOfACent: 6
```
