// Hooks run with workload-account AWS credentials, which cannot read the
// management-account backend. Hand off only the public URL through a local file.
resource "local_file" "endpoint" {
  filename        = "${path.module}/.stackrepeat-endpoint"
  content         = local.endpoint
  file_permission = "0600"
  depends_on      = [aws_ssm_parameter.site_url]
}

output "endpoint" {
  description = "Public HTTPS URL to attach to the workload. The post hook verifies readiness."
  value       = local.endpoint
  depends_on  = [aws_ssm_parameter.site_url]
}

output "admin_username" {
  description = "Automatically provisioned Mattermost administrator username."
  value       = "demo-admin"
}

output "admin_credentials_parameter" {
  description = "SSM SecureString parameter name; retrieve its JSON password field in the workload account."
  value       = aws_ssm_parameter.credentials.name
}

output "aws_region" {
  description = "AWS region containing the server and administrator credential."
  value       = data.aws_region.current.region
}

output "instance_id" {
  description = "EC2 instance to manage through Systems Manager Session Manager."
  value       = aws_instance.demo.id
}
