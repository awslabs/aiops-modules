import aws_cdk.aws_lambda as lambda_

MAX_BUCKET_NAME_LENGTH = 63
MAX_SQS_QUEUE_NAME_LENGTH = 80
MAX_FEATURE_GROUP_NAME_LENGTH = 64
MAX_ROLE_NAME_LENGTH = 64
MAX_STATE_MACHINE_NAME_LENGTH = 80
MAX_LAMBDA_FUNCTION_NAME_LENGTH = 64

# map of lambda function Id, you can see the current list here:
# https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_AnnotationConsolidationConfig.html#SageMaker-Type-AnnotationConsolidationConfig-AnnotationConsolidationLambdaArn
AC_ARN_MAP = {
    "us-east-1": "432418664414",
    "us-east-2": "266458841044",
    "us-west-2": "081040173940",
    "eu-west-1": "568282634449",
    "ap-northeast-1": "477331159723",
    "ap-southeast-2": "454466003867",
    "ap-south-1": "565803892007",
    "eu-central-1": "203001061592",
    "ap-northeast-2": "845288260483",
    "eu-west-2": "487402164563",
    "ap-southeast-1": "377565633583",
    "ca-central-1": "918755190332",
}

LAMBDA_RUNTIME = lambda_.Runtime.PYTHON_3_12
