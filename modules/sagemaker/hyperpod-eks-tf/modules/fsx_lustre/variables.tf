variable "resource_name_prefix" {
  description = "Prefix to be used for all resources created by this module"
  type        = string
  default     = "sagemaker-hyperpod-eks"
}


variable "private_subnet_id" {
  description = "The Id of the private subnet for HyperPod cross-account ENIs"
  type        = string
}

variable "security_group_id" {
  description = "The Id of your cluster security group"
  type        = string
}

variable "eks_cluster_name" {
  description = "The name of the EKS cluster"
  type        = string
}

variable "fsx_csi_driver_version" {
  type        = string
  description = "Version of the AWS FSx CSI driver Helm chart"
  default     = "1.11.0"
}

variable "capacity" {
  description = "Storage capacity in GiB (1200 or increments of 2400)"
  type        = number
  default     = 1200
}

variable "per_unit_storage_throughput" {
  description = "Provisioned Read/Write (MB/s/TiB)"
  type        = number
  default     = 1000
  validation {
    condition     = contains([125, 250, 500, 1000], var.per_unit_storage_throughput)
    error_message = "Per unit storage throughput must be one of: 125, 250, 500, or 1000"
  }
}

variable "compression" {
  description = "Data compression type"
  type        = string
  default     = "LZ4"
  validation {
    condition     = contains(["LZ4", "NONE"], var.compression)
    error_message = "Compression must be either LZ4 or NONE"
  }
}

variable "lustre_version" {
  description = "Lustre software version"
  type        = string
  default     = "2.15"
  validation {
    condition     = contains(["2.15", "2.12"], var.lustre_version)
    error_message = "Lustre version must be either 2.15 or 2.12"
  }
}

variable "s3_bucket_name" {
  description = "The name of the S3 bucket for Data Repository Association"
  type        = string
}
