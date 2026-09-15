data "aws_ami" "linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-6.1-x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_iam_role" "demo" {
  name_prefix = "${local.name}-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy" "session_manager" {
  role = aws_iam_role.demo.id
  # Session Manager access without the managed policy's account-wide parameter reads.
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ssm:UpdateInstanceInformation",
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ]
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy" "configuration" {
  role = aws_iam_role.demo.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["ssm:GetParameter"]
      Resource = [
        aws_ssm_parameter.credentials.arn,
        "arn:${data.aws_partition.current.partition}:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter${local.site_url_parameter_name}"
      ]
    }]
  })
}

resource "aws_iam_instance_profile" "demo" {
  name_prefix = "${local.name}-"
  role        = aws_iam_role.demo.name
  tags        = local.tags
}

resource "aws_instance" "demo" {
  ami                         = data.aws_ami.linux.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.demo.id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.demo.name
  user_data_replace_on_change = true

  user_data_base64 = base64gzip(templatefile("${path.module}/templates/bootstrap.sh.tftpl", {
    aws_region                 = data.aws_region.current.region
    site_url_parameter_name    = local.site_url_parameter_name
    credentials_parameter_name = aws_ssm_parameter.credentials.name
    mattermost_image           = local.mattermost_image
    postgres_image             = local.postgres_image
    compose_version            = local.compose_version
    compose_sha256             = local.compose_sha256
  }))

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    encrypted             = true
    delete_on_termination = true
    tags                  = local.tags
  }

  # Cap burst credit charges; sustained heavy demo load can be throttled.
  credit_specification {
    cpu_credits = "standard"
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  lifecycle {
    # A newly published AMI must not unexpectedly replace the demo's local data.
    ignore_changes = [ami]
  }

  tags = merge(local.tags, { Name = local.name })
  depends_on = [
    aws_route.internet,
    aws_route_table_association.public,
    aws_iam_role_policy.configuration,
    aws_iam_role_policy.session_manager
  ]
}

resource "aws_eip" "demo" {
  domain     = "vpc"
  instance   = aws_instance.demo.id
  tags       = local.tags
  depends_on = [aws_internet_gateway.demo]
}
