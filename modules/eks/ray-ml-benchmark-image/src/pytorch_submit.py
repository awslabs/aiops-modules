from ray.job_submission import JobSubmissionClient

client = JobSubmissionClient()

kick_off_pytorch_benchmark = (
    "ray --version\n"
    "rm -rf ray\n"
    # Clone ray. If ray is already present, don't clone again.
    "git clone https://github.com/ray-project/ray\n"
    "cd ray\n"
    "git fetch --all\n"
    "git checkout ray-2.3.0\n"
    # Run the benchmark.
    " python release/air_tests/air_benchmarks/workloads/tune_torch_benchmark.py\n"
)


submission_id = client.submit_job(
    entrypoint=kick_off_pytorch_benchmark,
)

print("Use the following command to follow this Job's logs:")
print(f"ray job logs '{submission_id}'")
