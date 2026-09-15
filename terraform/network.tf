# A single public subnet avoids NAT gateways and baseline network dependencies.
resource "aws_vpc" "demo" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(local.tags, { Name = local.name })
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.demo.id
  cidr_block        = "10.42.0.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags              = merge(local.tags, { Name = "${local.name}-public" })
}

resource "aws_internet_gateway" "demo" {
  vpc_id = aws_vpc.demo.id
  tags   = local.tags
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.demo.id
  tags   = local.tags
}

resource "aws_route" "internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.demo.id
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

resource "aws_security_group" "demo" {
  name_prefix = "${local.name}-"
  description = "HTTP origin access from CloudFront only; management via SSM"
  vpc_id      = aws_vpc.demo.id
  tags        = local.tags
}

resource "aws_vpc_security_group_ingress_rule" "cloudfront" {
  security_group_id = aws_security_group.demo.id
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront.id
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "demo" {
  security_group_id = aws_security_group.demo.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "OS packages, container registry and AWS management APIs"
}
