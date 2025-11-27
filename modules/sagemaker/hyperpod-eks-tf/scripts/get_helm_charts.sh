#!/bin/bash

set +x

echo "Starting git clone operation..."
echo "Cleaning up existing directory..."
rm -rf /tmp/helm-repo
echo "Creating fresh directory..."
mkdir -p /tmp/helm-repo
echo "Cloning from https://github.com/aws/sagemaker-hyperpod-cli.git..."
git clone https://github.com/aws/sagemaker-hyperpod-cli.git /tmp/helm-repo
echo "Contents of /tmp/helm-repo:"
ls -la /tmp/helm-repo
echo "Git clone complete"