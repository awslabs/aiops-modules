terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.0.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 3.0.2"
    }
    http = {
      source  = "hashicorp/http"
      version = ">= 3.0"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.0.0"
    }
  }
  required_version = ">= 1.0.0"

  backend "s3" {
    key          = "backend/terraform.tfstate"
    bucket = "aiops-hyperpod-eks-artifacts-bucket-181ff6f2-6e211731e636b81"
    region = "us-east-2"
    use_lockfile = true
  }
}
