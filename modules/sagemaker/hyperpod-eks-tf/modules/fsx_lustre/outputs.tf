output "fsx_filesystem_id" {
  value = aws_fsx_lustre_file_system.this.id
}

output "fsx_mount_name" {
  value = aws_fsx_lustre_file_system.this.mount_name
}

output "fsx_dns_name" {
  value = aws_fsx_lustre_file_system.this.dns_name
}

output "storage_class_name" {
  value = kubernetes_storage_class.fsx.metadata[0].name
}
