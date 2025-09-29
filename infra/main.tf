terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "tradepulse-terraform-state-590183672693"
    key    = "terraform.tfstate"
    region = "eu-west-2"
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Repository  = var.github_repo
    }
  }
}

# Route53 zone lookup (used when hosted_zone_id not explicitly provided)
data "aws_route53_zone" "primary" {
  count = 0
  name  = var.domain_name
}

# Additional provider for us-east-1 (ACM for CloudFront)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# Frontend S3 bucket (private) and CloudFront (OAC)
resource "aws_s3_bucket" "frontend" {
  count  = var.domain_name != "" ? 1 : 0
  bucket = "${var.project_name}-frontend-${data.aws_caller_identity.current.account_id}-${var.region}"
}

resource "aws_s3_bucket_ownership_controls" "frontend" {
  count  = length(aws_s3_bucket.frontend) == 0 ? 0 : 1
  bucket = aws_s3_bucket.frontend[0].id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  count                   = length(aws_s3_bucket.frontend) == 0 ? 0 : 1
  bucket                  = aws_s3_bucket.frontend[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "oac" {
  count                             = var.domain_name != "" ? 1 : 0
  name                              = "${var.project_name}-frontend-oac"
  description                       = "OAC for ${var.project_name} frontend"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_acm_certificate" "frontend" {
  provider                  = aws.us_east_1
  count                     = var.domain_name != "" ? 1 : 0
  domain_name               = "${var.frontend_subdomain}.${var.domain_name}"
  subject_alternative_names = [var.domain_name]
  validation_method         = "DNS"
}

resource "aws_route53_record" "frontend_cert_validation" {
  for_each = length(aws_acm_certificate.frontend) == 0 ? {} : {
    for dvo in aws_acm_certificate.frontend[0].domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  }
  zone_id = var.hosted_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "frontend" {
  provider                = aws.us_east_1
  count                   = length(aws_acm_certificate.frontend) == 0 ? 0 : 1
  certificate_arn         = aws_acm_certificate.frontend[0].arn
  validation_record_fqdns = [for r in aws_route53_record.frontend_cert_validation : r.fqdn]
}

# CloudFront Function for URL rewriting (directory index)
resource "aws_cloudfront_function" "url_rewrite" {
  count   = var.domain_name != "" ? 1 : 0
  name    = "${var.project_name}-url-rewrite"
  runtime = "cloudfront-js-2.0"
  comment = "Rewrite URLs to append /index.html for directory requests"
  publish = true
  code    = <<-EOT
function handler(event) {
  var request = event.request;
  var uri = request.uri;
  
  // If URI ends with '/', append 'index.html'
  if (uri.endsWith('/')) {
    request.uri += 'index.html';
  }
  // If URI has no extension, append '/index.html'
  else if (!uri.includes('.')) {
    request.uri += '/index.html';
  }
  
  return request;
}
EOT
}

resource "aws_cloudfront_distribution" "frontend" {
  count = var.domain_name != "" ? 1 : 0

  enabled             = true
  comment             = "${var.project_name} frontend"
  default_root_object = "index.html"

  aliases = [
    "${var.frontend_subdomain}.${var.domain_name}",
    var.domain_name
  ]

  origin {
    domain_name              = aws_s3_bucket.frontend[0].bucket_regional_domain_name
    origin_id                = aws_s3_bucket.frontend[0].id
    origin_access_control_id = aws_cloudfront_origin_access_control.oac[0].id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = aws_s3_bucket.frontend[0].id
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    # Attach URL rewrite function
    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.url_rewrite[0].arn
    }
  }

  # Custom error response only for 404 (client-side routing fallback)
  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.frontend[0].certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

resource "aws_route53_record" "frontend_alias" {
  count   = length(aws_cloudfront_distribution.frontend) == 0 ? 0 : 1
  zone_id = var.hosted_zone_id
  name    = "${var.frontend_subdomain}.${var.domain_name}"
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.frontend[0].domain_name
    zone_id                = aws_cloudfront_distribution.frontend[0].hosted_zone_id
    evaluate_target_health = false
  }
}

# Apex alias to CloudFront so root domain serves the app as well
resource "aws_route53_record" "frontend_apex_alias" {
  count   = length(aws_cloudfront_distribution.frontend) == 0 ? 0 : 1
  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.frontend[0].domain_name
    zone_id                = aws_cloudfront_distribution.frontend[0].hosted_zone_id
    evaluate_target_health = false
  }
}

# Bucket policy to allow CloudFront (OAC) to read objects
data "aws_iam_policy_document" "frontend_s3_policy" {
  count = length(aws_cloudfront_distribution.frontend) == 0 ? 0 : 1

  statement {
    sid     = "AllowCloudFrontReadOAC"
    actions = ["s3:GetObject"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    resources = [
      "${aws_s3_bucket.frontend[0].arn}/*"
    ]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.frontend[0].arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend_oac" {
  count  = length(data.aws_iam_policy_document.frontend_s3_policy) == 0 ? 0 : 1
  bucket = aws_s3_bucket.frontend[0].id
  policy = data.aws_iam_policy_document.frontend_s3_policy[0].json
}

output "frontend_url" {
  description = "Frontend CloudFront URL"
  value       = length(aws_cloudfront_distribution.frontend) == 0 ? null : aws_cloudfront_distribution.frontend[0].domain_name
}

output "frontend_bucket_name" {
  description = "Frontend S3 bucket name"
  value       = length(aws_s3_bucket.frontend) == 0 ? null : aws_s3_bucket.frontend[0].id
}

output "frontend_distribution_id" {
  description = "Frontend CloudFront distribution ID"
  value       = length(aws_cloudfront_distribution.frontend) == 0 ? null : aws_cloudfront_distribution.frontend[0].id
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ECR Repository for backend images
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }


  tags = {
    Name = "${var.project_name}-backend-ecr"
  }
}

# ECR Lifecycle Policy (separate resource)
resource "aws_ecr_lifecycle_policy" "backend_lifecycle" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 20 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# ECR Repository policy for GitHub Actions
resource "aws_ecr_repository_policy" "backend_policy" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowGitHubActions"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.github_actions.arn
        }
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
      }
    ]
  })
}

# Outputs
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.backend.repository_url
}

output "app_runner_service_url" {
  description = "App Runner service URL"
  value       = aws_apprunner_service.backend.service_url
}

output "app_runner_service_arn" {
  description = "App Runner service ARN"
  value       = aws_apprunner_service.backend.arn
}

# Optional: Route 53 records for custom domain
locals {
  backend_fqdn = var.domain_name != "" ? (var.apex_subdomain != "" ? "${var.apex_subdomain}.${var.domain_name}" : var.domain_name) : ""
}

resource "aws_route53_record" "backend_alias" {
  count           = local.backend_fqdn != "" ? 1 : 0
  zone_id         = var.hosted_zone_id
  name            = local.backend_fqdn
  type            = "CNAME"
  ttl             = 60
  allow_overwrite = true
  records         = [aws_apprunner_service.backend.service_url]
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    signals     = aws_dynamodb_table.signals.name
    portfolio   = aws_dynamodb_table.portfolio.name
    positions   = aws_dynamodb_table.positions.name
    analytics   = aws_dynamodb_table.analytics.name
    brain_state = aws_dynamodb_table.brain_state.name
    runtime     = aws_dynamodb_table.runtime.name
    market_data = aws_dynamodb_table.market_data.name
  }
}

output "github_role_arn" {
  description = "GitHub Actions IAM role ARN"
  value       = aws_iam_role.github_actions.arn
}
