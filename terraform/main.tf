data "aws_region" "current" {}
data "aws_partition" "current" {}
data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

resource "random_id" "deployment" {
  byte_length = 4
}

locals {
  name = "mattermost-${random_id.deployment.hex}"
  tags = {
    Blueprint = "mattermost-demo"
    ManagedBy = "StackRepeat"
    Purpose   = "demo"
  }
  endpoint                = "https://${aws_cloudfront_distribution.demo.domain_name}"
  site_url_parameter_name = "/stackrepeat/${local.name}/site-url"

  # Pinned upstream binaries and images; no custom image build is required.
  mattermost_image = "mattermost/mattermost-team-edition:11.10.1@sha256:8285b96eb412d89dd308e4c1ad9cc7f1a9dc9edcd798167b55bc35f1c7ee69d1"
  postgres_image   = "postgres:17.10-alpine@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193"
  compose_version  = "v5.5.1"
  compose_sha256   = "db1889184726840f75c4f9c001048430d4f25b3be3cb084d3ddd762bc0aed576"
}
