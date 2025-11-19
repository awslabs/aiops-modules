data "aws_partition" "current" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Get the OIDC provider URL for the EKS cluster
data "aws_eks_cluster" "cluster" {
  name = var.eks_cluster_name
}

data "tls_certificate" "eks" {
  url = data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer
}

# Create the OIDC Provider
resource "aws_iam_openid_connect_provider" "eks_provider" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer
}


# Create IAM role for the service account
resource "aws_iam_role" "fsx_csi_controller" {
  name = "FSXLCSI-${var.eks_cluster_name}-${data.aws_region.current.region}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks_provider.arn
        }
        Condition = {
          StringEquals = {
            "${replace(aws_iam_openid_connect_provider.eks_provider.url, "https://", "")}:sub": "system:serviceaccount:kube-system:fsx-csi-controller-sa"
            "${replace(aws_iam_openid_connect_provider.eks_provider.url, "https://", "")}:aud": "sts.amazonaws.com"
          }
        }
      }
    ]
  })
}

# Attach the FSx policy to the role
resource "aws_iam_role_policy_attachment" "fsx_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonFSxFullAccess"
  role       = aws_iam_role.fsx_csi_controller.name
}

resource "kubernetes_service_account" "fsx_csi_controller" {
  metadata {
    name      = "fsx-csi-controller-sa"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.fsx_csi_controller.arn
    }
  }
}

resource "helm_release" "aws_fsx_csi_driver" {
  name       = "aws-fsx-csi-driver"
  repository = "https://kubernetes-sigs.github.io/aws-fsx-csi-driver"
  chart      = "aws-fsx-csi-driver"
  namespace  = "kube-system"
  version    = var.fsx_csi_driver_version

  values = [
    yamlencode({
      controller = {
        serviceAccount = {
          create = false
        }
      }
    })
  ]

  depends_on = [
    kubernetes_service_account.fsx_csi_controller,
    aws_iam_role.fsx_csi_controller
  ]
}

resource "aws_fsx_lustre_file_system" "this" {
  storage_capacity            = var.capacity
  subnet_ids                  = [var.private_subnet_id]
  security_group_ids          = [var.security_group_id]
  storage_type                = "SSD"
  deployment_type             = "PERSISTENT_2"
  per_unit_storage_throughput = var.per_unit_storage_throughput
  file_system_type_version    = var.lustre_version
  data_compression_type       = var.compression
  efa_enabled                 = true
  metadata_configuration {
    mode = "AUTOMATIC"
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "ai-poc-fsx-lustre-filesystem"
  }
}

resource "aws_fsx_data_repository_association" "dra" {
  file_system_id       = aws_fsx_lustre_file_system.this.id
  data_repository_path = "s3://${var.s3_bucket_name}"
  file_system_path     = "/"

  s3 {
    auto_export_policy {
      events = ["NEW", "CHANGED", "DELETED"]
    }

    auto_import_policy {
      events = ["NEW", "CHANGED", "DELETED"]
    }
  }
}

resource "kubernetes_storage_class" "fsx" {
  metadata {
    name = "fsx-sc"
  }

  storage_provisioner = "fsx.csi.aws.com"
  
  parameters = {
    subnetId                     = var.private_subnet_id
    securityGroupIds             = var.security_group_id
    deploymentType               = "PERSISTENT_2"
    automaticBackupRetentionDays = "0"
    copyTagsToBackups            = "true"
    perUnitStorageThroughput     = "1000"
    dataCompressionType          = "LZ4"
    fileSystemTypeVersion        = "2.15"
  }

  mount_options = ["flock"]
    
  depends_on = [
    resource.helm_release.aws_fsx_csi_driver
  ]

}

resource "kubernetes_persistent_volume" "fsx" {
  metadata {
    name = "fsx-pv"
  }

  spec {
    capacity = {
      storage = "9600Gi"
    }
    
    volume_mode = "Filesystem"
    access_modes = ["ReadWriteMany"]
    persistent_volume_reclaim_policy = "Retain"
    storage_class_name = kubernetes_storage_class.fsx.metadata[0].name

    persistent_volume_source {
      csi {
        driver = "fsx.csi.aws.com"
        volume_handle = aws_fsx_lustre_file_system.this.id
        # volume_attributes removed - FSx CSI driver will auto-discover these values
        # volume_attributes = {
        #   dnsname   = "${aws_fsx_lustre_file_system.this.id}.fsx.${data.aws_region.current.region}.amazonaws.com"
        #   mountname = aws_fsx_lustre_file_system.this.mount_name
        # }
      }
    }
  }

  depends_on = [
    kubernetes_storage_class.fsx
  ]
}


resource "kubernetes_persistent_volume_claim" "fsx" {
  metadata {
    name      = "fsx-claim"
    namespace = "default"  
  }

  spec {
    access_modes = ["ReadWriteMany"]
    storage_class_name = kubernetes_storage_class.fsx.metadata[0].name

    resources {
      requests = {
        storage = "9600Gi"
      }
    }
  }

  depends_on = [
    kubernetes_persistent_volume.fsx
  ]
}

resource "kubernetes_pod" "fsx_app" {
  metadata {
    name = "fsx-app"
  }

  spec {
    container {
      name    = "app"
      image   = "ubuntu"
      command = ["/bin/sh"]
      args    = ["-c", "while true; do echo $(date -u) >> /data/out.txt; sleep 5; done"]

      volume_mount {
        name       = "persistent-storage"
        mount_path = "/data"
      }
    }

    volume {
      name = "persistent-storage"
      persistent_volume_claim {
        claim_name = kubernetes_persistent_volume_claim.fsx.metadata[0].name
      }
    }
  }

  depends_on = [
    kubernetes_persistent_volume_claim.fsx,
    kubernetes_persistent_volume.fsx,
    helm_release.aws_fsx_csi_driver
  ]
}
