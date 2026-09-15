mock_provider "aws" {
  mock_data "aws_region" {
    defaults = { region = "us-east-1" }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-1a", "us-east-1b"] }
  }
  mock_data "aws_ami" {
    defaults = { id = "ami-0123456789abcdef0" }
  }
  mock_data "aws_ec2_managed_prefix_list" {
    defaults = { id = "pl-12345678" }
  }
  mock_resource "aws_eip" {
    defaults = { public_dns = "ec2-203-0-113-10.compute-1.amazonaws.com" }
  }
  mock_resource "aws_cloudfront_distribution" {
    defaults = { domain_name = "demo.cloudfront.net" }
  }
  mock_resource "aws_ssm_parameter" {
    defaults = { arn = "arn:aws:ssm:us-east-1:123456789012:parameter/demo" }
  }
}

mock_provider "random" {
  mock_resource "random_id" {
    defaults = { hex = "a1b2c3d4" }
  }
}

mock_provider "local" {}

run "demo_contract" {
  command = apply

  assert {
    condition     = output.endpoint == "https://demo.cloudfront.net"
    error_message = "The workload must expose the HTTPS application endpoint."
  }
  assert {
    condition     = local_file.endpoint.content == output.endpoint && local_file.endpoint.file_permission == "0600"
    error_message = "The hook must receive the public URL without reading the protected state backend."
  }
  assert {
    condition     = length(aws_instance.demo.user_data_base64) <= 21844
    error_message = "Compressed bootstrap must fit EC2's 16 KiB decoded user-data limit."
  }
  assert {
    condition     = aws_instance.demo.instance_type == "t3a.small" && aws_instance.demo.credit_specification[0].cpu_credits == "standard"
    error_message = "The default should remain a small server without surplus CPU credit charges."
  }
  assert {
    condition     = aws_instance.demo.root_block_device[0].encrypted && aws_instance.demo.root_block_device[0].delete_on_termination && aws_instance.demo.root_block_device[0].volume_size == 30
    error_message = "The demo must use an encrypted 30 GiB disk that is removed on destroy."
  }
  assert {
    condition     = aws_instance.demo.metadata_options[0].http_tokens == "required" && aws_instance.demo.metadata_options[0].http_put_response_hop_limit == 1
    error_message = "Require IMDSv2 and keep instance credentials out of containers."
  }
  assert {
    condition     = aws_vpc_security_group_ingress_rule.cloudfront.prefix_list_id == "pl-12345678" && aws_vpc_security_group_ingress_rule.cloudfront.from_port == 80
    error_message = "Only CloudFront may reach the public proxy."
  }
  assert {
    condition     = aws_cloudfront_distribution.demo.default_cache_behavior[0].viewer_protocol_policy == "redirect-to-https"
    error_message = "Browsers must use HTTPS."
  }
  assert {
    condition     = aws_ssm_parameter.credentials.type == "SecureString" && aws_ssm_parameter.site_url.value == output.endpoint
    error_message = "Store bootstrap credentials securely and publish the same SiteURL the workload exposes."
  }
}

run "unsupported_arm_instance" {
  command = plan
  variables {
    instance_type = "t4g.small"
  }
  expect_failures = [var.instance_type]
}
