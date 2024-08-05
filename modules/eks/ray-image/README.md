# Introduction

## Description

This module demonstrates an example on how to build a custom Ray Docker image. The image is pushed to AWS ECR with enabled scan on push.

### Required Parameters

- `ecr-repo-name`: ECR Repository name to be used/created if it doesn't exist.

### Sample manifest declaration

```yaml
name: ray
path: modules/eks/ray-image
targetAccount: primary
parameters:
  - name: ecr-repo-name
    valueFrom:
      moduleMetadata:
        group: base
        name: ray-ecr
        key: EcrRepositoryName
```

### Module Metadata Outputs

- `ImageUri`: URI of the image
