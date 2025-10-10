kubernetes_version = "1.32"
create_hyperpod_module = true
# Default instance group for hyperpod
instance_groups = {
    accelerated-instance-group-1 = {
        instance_type = "ml.g5.xlarge",
        instance_count = 1,
        ebs_volume_size = 400,
        threads_per_core = 2,
        enable_stress_check = false,
        enable_connectivity_check = false,
        lifecycle_script = "on_create.sh",
        training_plan_arn = ""  # Set to training plan ARN if using training plans
    }
}
