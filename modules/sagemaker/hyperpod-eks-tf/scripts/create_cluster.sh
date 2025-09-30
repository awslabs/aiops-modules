#!/bin/bash

cat > cluster-config.json << EOL
{
    "ClusterName": "${HYPERPOD_CLUSTER_NAME}",
    "Orchestrator": {
        "Eks":
        {
        "ClusterArn": "${EKS_CLUSTER_ARN}"
        }
    },
    "InstanceGroups": [
        {
        "InstanceGroupName": "worker-group-1",
        "InstanceType": "${ACCEL_INSTANCE_TYPE}",
        "InstanceCount": ${ACCEL_COUNT},
        "InstanceStorageConfigs": [
            {
            "EbsVolumeConfig": {
                "VolumeSizeInGB": ${ACCEL_VOLUME_SIZE}
            }
            }
        ],
        "LifeCycleConfig": {
            "SourceS3Uri": "s3://${S3_BUCKET_NAME}/lifecycle_scripts/",
            "OnCreate": "on_create.sh"
        },
        "TrainingPlanArn": "${TRAINING_PLAN_ARN}",
        "ExecutionRole": "${SAGEMAKER_IAM_ROLE_ARN}",
        "ThreadsPerCore": 2
        }
    ],
    "VpcConfig": {
        "SecurityGroupIds": ["$SECURITY_GROUP_ID"],
        "Subnets":["$PRIVATE_SUBNET_ID"]
    },
    "NodeRecovery": "${NODE_RECOVERY}"
}
EOL

aws sagemaker create-cluster --cli-input-json file://cluster-config.json --region $AWS_REGION