resource "random_password" "admin" {
  length  = 32
  special = false
}

# No secret values in EC2 user data or public workload outputs. Terraform state
# still contains generated secrets and must use the platform's protected backend.
resource "aws_ssm_parameter" "credentials" {
  name        = "/stackrepeat/${local.name}/credentials"
  description = "Initial Mattermost administrator and CloudFront origin credential"
  type        = "SecureString"
  tier        = "Standard"
  value = jsonencode({
    username     = "demo-admin"
    email        = "demo-admin@example.invalid"
    password     = random_password.admin.result
    origin_token = random_password.origin.result
  })
  tags = local.tags
}

# The host waits for this after CloudFront is created, avoiding a dependency cycle.
resource "aws_ssm_parameter" "site_url" {
  name  = local.site_url_parameter_name
  type  = "String"
  tier  = "Standard"
  value = local.endpoint
  tags  = local.tags
}
