resource "random_password" "origin" {
  length  = 48
  special = false
}

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "viewer" {
  name = "Managed-AllViewer"
}

resource "aws_cloudfront_distribution" "demo" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${local.name}: Mattermost demo"
  price_class         = "PriceClass_100"
  wait_for_deployment = true
  retain_on_delete    = false

  origin {
    domain_name = aws_eip.demo.public_dns
    origin_id   = "mattermost"
    custom_header {
      name  = "X-StackRepeat-Origin"
      value = random_password.origin.result
    }
    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "http-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60
      origin_keepalive_timeout = 60
    }
  }

  default_cache_behavior {
    target_origin_id         = "mattermost"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.viewer.id
    compress                 = true
  }

  # Avoid cached startup failures while cloud-init is preparing the application.
  dynamic "custom_error_response" {
    for_each = toset([500, 502, 503, 504])
    content {
      error_code            = custom_error_response.value
      error_caching_min_ttl = 0
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  viewer_certificate {
    cloudfront_default_certificate = true
  }
  tags = local.tags
}
