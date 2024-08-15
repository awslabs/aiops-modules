import os
import sys
from unittest import mock

import pytest
from pydantic import ValidationError


@pytest.fixture(scope="function")
def stack_defaults():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
        os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
        os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
        os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
        os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

        os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_NAME"] = "cluster"
        os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_ADMIN_ROLE_ARN"] = (
            "arn:aws:iam::123456789012:role/eks-testing-XXXXXX"
        )
        os.environ["SEEDFARMER_PARAMETER_EKS_OIDC_ARN"] = (
            "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/XXXXXXXX"
        )
        os.environ["SEEDFARMER_PARAMETER_EKS_OPENID_ISSUER"] = "sts.amazon.com"
        os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_ENDPOINT"] = "oidc.eks.us-west-2.amazonaws.com/id/XXXXXXXXXX"
        os.environ["SEEDFARMER_PARAMETER_EKS_CERT_AUTH_DATA"] = "cert"
        os.environ["SEEDFARMER_PARAMETER_EKS_HANDLER_ROLE_ARN"] = "arn:aws:iam::123456789012:role/eks-test-YYYYYY"
        os.environ["SEEDFARMER_PARAMETER_NAMESPACE"] = "namespace"

        # Unload the app import so that subsequent tests don't reuse
        if "app" in sys.modules:
            del sys.modules["app"]

        yield


def test_app(stack_defaults):
    import app  # noqa: F401


def test_eks_cluster_name(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_NAME"]

    with pytest.raises(ValidationError):
        import app  # noqa: F401
