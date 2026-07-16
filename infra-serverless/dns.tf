# Variant B (user-approved 2026-07-16): bot.tradepulseai.co.uk → CloudFront →
# status Lambda function URL. Domain is registered in Route53 Domains (this
# account) until 2026-09-29; the original hosted zone was deleted in the old
# teardown, so we create a fresh one and point the registrar at it.

provider "aws" {
  alias  = "us_east_1" # CloudFront certificates must live in us-east-1
  region = "us-east-1"

  default_tags {
    tags = {
      Project   = "tradepulse"
      Stack     = "serverless-paper-bot"
      ManagedBy = "terraform"
    }
  }
}

variable "domain_name" {
  type    = string
  default = "tradepulseai.co.uk"
}

variable "bot_subdomain" {
  type    = string
  default = "bot"
}

locals {
  bot_fqdn = "${var.bot_subdomain}.${var.domain_name}"
  # hostname (no scheme) of the status Lambda function URL
  status_lambda_host = replace(replace(aws_lambda_function_url.status.function_url, "https://", ""), "/", "")
}

# ------------------------------------------------------------------- Zone --
resource "aws_route53_zone" "main" {
  name    = var.domain_name
  comment = "TradePulse — recreated 2026-07-16 (original zone deleted in teardown)"
}

# Point the Route53 Domains registrar at the new zone's nameservers.
resource "aws_route53domains_registered_domain" "main" {
  domain_name = var.domain_name

  dynamic "name_server" {
    for_each = aws_route53_zone.main.name_servers
    content {
      name = name_server.value
    }
  }
}

# ------------------------------------------------------------- Certificate --
resource "aws_acm_certificate" "bot" {
  provider          = aws.us_east_1
  domain_name       = local.bot_fqdn
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "bot_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.bot.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id = aws_route53_zone.main.zone_id
  name    = each.value.name
  type    = each.value.type
  ttl     = 300
  records = [each.value.record]
}

resource "aws_acm_certificate_validation" "bot" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.bot.arn
  validation_record_fqdns = [for r in aws_route53_record.bot_cert_validation : r.fqdn]

  timeouts {
    create = "45m" # NS delegation must propagate before DNS validation succeeds
  }
}

# -------------------------------------------------------------- CloudFront --
resource "aws_cloudfront_distribution" "bot" {
  enabled         = true
  comment         = "bot.tradepulseai.co.uk -> paper bot status Lambda"
  aliases         = [local.bot_fqdn]
  price_class     = "PriceClass_100" # EU+NA edges only — cheapest
  http_version    = "http2and3"
  is_ipv6_enabled = true

  origin {
    domain_name = local.status_lambda_host
    origin_id   = "status-lambda"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "status-lambda"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    # status must stay fresh; cache only briefly at the edge
    cache_policy_id            = aws_cloudfront_cache_policy.bot_short.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.bot.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

resource "aws_cloudfront_cache_policy" "bot_short" {
  name        = "tradepulse-bot-status-short"
  default_ttl = 30
  max_ttl     = 60
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "all" # ?format=json must be part of the key
    }
    enable_accept_encoding_gzip   = true
    enable_accept_encoding_brotli = true
  }
}

# Lambda function URLs reject requests whose Host header isn't the URL's own
# hostname — this managed policy forwards everything EXCEPT Host.
data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

resource "aws_route53_record" "bot" {
  zone_id = aws_route53_zone.main.zone_id
  name    = local.bot_fqdn
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.bot.domain_name
    zone_id                = aws_cloudfront_distribution.bot.hosted_zone_id
    evaluate_target_health = false
  }
}

output "bot_url" {
  value = "https://${local.bot_fqdn}"
}

output "zone_nameservers" {
  value = aws_route53_zone.main.name_servers
}
