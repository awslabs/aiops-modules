kubernetes_version = "1.32"
eks_cluster_name = "eks-1"
hyperpod_cluster_name = "hyperpod-1"
resource_name_prefix = "ai-poc"
# Default instance group for hyperpod
# Will not be used if Flexible Training Plan Arn is provided
instance_groups = {
    accelerated-instance-group-1 = {
        instance_type = "ml.g5.xlarge",
        instance_count = 1,
        ebs_volume_size = 400,
        threads_per_core = 2,
        enable_stress_check = false,
        enable_connectivity_check = false,
        lifecycle_script = "on_create.sh"
    }
}
