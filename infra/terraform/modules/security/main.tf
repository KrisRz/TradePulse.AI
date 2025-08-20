# TradePulse.AI - Security Module
# WAF, Secrets Manager, SSL Certificates, IAM
# Enterprise-grade security infrastructure

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
      configuration_aliases = [aws.us_east_1]
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}-${var.deployment_id}"
  
  common_tags = merge(var.tags, {
    Module = "security"
    Service = "security-services"
  })
}

# ============================================================================
# SECRETS MANAGER
# ============================================================================

resource "aws_secretsmanager_secret" "secrets" {
  for_each = var.secrets_config
  
  name         = "${local.name_prefix}/${each.key}"
  description  = "Secret for ${each.key} - ${var.environment}"
  
  # Deletion protection
  recovery_window_in_days = var.environment == "production" ? 30 : 7
  
  tags = merge(local.common_tags, {
    SecretType = each.key
    Environment = var.environment
  })
}

# Secret versions
resource "aws_secretsmanager_secret_version" "secrets" {
  for_each = var.secrets_config
  
  secret_id     = aws_secretsmanager_secret.secrets[each.key].id
  secret_string = each.value
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ============================================================================
# SSL/TLS CERTIFICATES
# ============================================================================

# ACM Certificate (if domain is provided)
resource "aws_acm_certificate" "main" {
  count = var.domain_name != "" ? 1 : 0
  provider = aws.us_east_1
  
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"
  
  lifecycle {
    create_before_destroy = true
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-certificate"
    Domain = var.domain_name
  })
}

# Route53 Zone (if managing DNS)
data "aws_route53_zone" "main" {
  count = var.domain_name != "" && var.manage_dns ? 1 : 0
  
  name         = var.domain_name
  private_zone = false
}

# Certificate validation records
resource "aws_route53_record" "cert_validation" {
  for_each = var.domain_name != "" && var.manage_dns ? {
    for dvo in aws_acm_certificate.main[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}
  
  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main[0].zone_id
}

# Certificate validation
resource "aws_acm_certificate_validation" "main" {
  count = var.domain_name != "" && var.manage_dns ? 1 : 0
  provider = aws.us_east_1
  
  certificate_arn         = aws_acm_certificate.main[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
  
  timeouts {
    create = "10m"
  }
}

# ============================================================================
# AWS WAF
# ============================================================================

resource "aws_wafv2_web_acl" "main" {
  count = var.enable_waf ? 1 : 0
  
  name  = "${local.name_prefix}-waf"
  scope = "CLOUDFRONT"
  
  default_action {
    allow {}
  }
  
  # Rule 1: Rate limiting
  rule {
    name     = "RateLimiting"
    priority = 1
    
    action {
      block {}
    }
    
    statement {
      rate_based_statement {
        limit              = var.rate_limit_per_ip
        aggregate_key_type = "IP"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-RateLimit"
      sampled_requests_enabled   = true
    }
  }
  
  # Rule 2: AWS Managed Core Rule Set
  rule {
    name     = "AWSManagedRulesCore"
    priority = 10
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-CoreRuleSet"
      sampled_requests_enabled   = true
    }
  }
  
  # Rule 3: Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputs"
    priority = 20
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-KnownBadInputs"
      sampled_requests_enabled   = true
    }
  }
  
  # Rule 4: SQL Injection Protection
  rule {
    name     = "AWSManagedRulesSQLInjection"
    priority = 30
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-SQLInjection"
      sampled_requests_enabled   = true
    }
  }
  
  # Rule 5: Geographic restrictions (if specified)
  dynamic "rule" {
    for_each = length(var.allowed_countries) > 0 ? [1] : []
    content {
      name     = "GeoRestriction"
      priority = 40
      
      action {
        block {}
      }
      
      statement {
        not_statement {
          statement {
            geo_match_statement {
              country_codes = var.allowed_countries
            }
          }
        }
      }
      
      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${local.name_prefix}-GeoRestriction"
        sampled_requests_enabled   = true
      }
    }
  }
  
  # Rule 6: Custom IP whitelist (if specified)
  dynamic "rule" {
    for_each = length(var.allowed_cidr_blocks) > 0 && var.allowed_cidr_blocks != ["0.0.0.0/0"] ? [1] : []
    content {
      name     = "IPWhitelist"
      priority = 5
      
      action {
        allow {}
      }
      
      statement {
        ip_set_reference_statement {
          arn = aws_wafv2_ip_set.allowed_ips[0].arn
        }
      }
      
      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${local.name_prefix}-IPWhitelist"
        sampled_requests_enabled   = true
      }
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name_prefix}-WAF"
    sampled_requests_enabled   = true
  }
  
  tags = local.common_tags
}

# IP Set for allowed IPs (if not allowing all)
resource "aws_wafv2_ip_set" "allowed_ips" {
  count = var.enable_waf && length(var.allowed_cidr_blocks) > 0 && var.allowed_cidr_blocks != ["0.0.0.0/0"] ? 1 : 0
  
  name  = "${local.name_prefix}-allowed-ips"
  scope = "CLOUDFRONT"
  
  ip_address_version = "IPV4"
  addresses          = var.allowed_cidr_blocks
  
  tags = local.common_tags
}

# WAF Logging Configuration
resource "aws_wafv2_web_acl_logging_configuration" "main" {
  count = var.enable_waf ? 1 : 0
  
  resource_arn            = aws_wafv2_web_acl.main[0].arn
  log_destination_configs = [aws_cloudwatch_log_group.waf[0].arn]
  
  redacted_fields {
    single_header {
      name = "authorization"
    }
  }
  
  redacted_fields {
    single_header {
      name = "cookie"
    }
  }
}

# CloudWatch Log Group for WAF
resource "aws_cloudwatch_log_group" "waf" {
  count = var.enable_waf ? 1 : 0
  
  name              = "/aws/wafv2/${local.name_prefix}"
  retention_in_days = var.waf_log_retention_days
  
  tags = local.common_tags
}

# ============================================================================
# IAM POLICIES AND ROLES
# ============================================================================

# IAM policy for accessing secrets
resource "aws_iam_policy" "secrets_access" {
  name        = "${local.name_prefix}-secrets-access"
  description = "Policy for accessing application secrets"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          for secret in aws_secretsmanager_secret.secrets : secret.arn
        ]
      }
    ]
  })
  
  tags = local.common_tags
}

# ============================================================================
# SECURITY GROUPS FOR EXTERNAL SERVICES
# ============================================================================

# Security group for external API access (if needed)
resource "aws_security_group" "external_api" {
  count = var.create_external_api_sg ? 1 : 0
  
  name        = "${local.name_prefix}-external-api-sg"
  description = "Security group for external API access"
  vpc_id      = var.vpc_id
  
  # HTTPS inbound from allowed CIDR blocks
  dynamic "ingress" {
    for_each = var.allowed_cidr_blocks
    content {
      description = "HTTPS from ${ingress.value}"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }
  
  # HTTP inbound from allowed CIDR blocks (if needed)
  dynamic "ingress" {
    for_each = var.allow_http ? var.allowed_cidr_blocks : []
    content {
      description = "HTTP from ${ingress.value}"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }
  
  # All outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-external-api-sg"
    Type = "external-api-security-group"
  })
}

# ============================================================================
# KMS KEYS FOR ADDITIONAL ENCRYPTION
# ============================================================================

# KMS Key for application-level encryption
resource "aws_kms_key" "application" {
  count = var.create_application_kms_key ? 1 : 0
  
  description             = "KMS key for application encryption - ${local.name_prefix}"
  deletion_window_in_days = var.environment == "production" ? 30 : 7
  enable_key_rotation     = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowApplicationAccess"
        Effect = "Allow"
        Principal = {
          AWS = var.lambda_role_arn != "" ? var.lambda_role_arn : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Service = "application-encryption"
  })
}

# KMS Key alias
resource "aws_kms_alias" "application" {
  count = var.create_application_kms_key ? 1 : 0
  
  name          = "alias/${local.name_prefix}-application"
  target_key_id = aws_kms_key.application[0].key_id
}

# ============================================================================
# CLOUDTRAIL FOR AUDIT LOGGING
# ============================================================================

resource "aws_cloudtrail" "main" {
  count = var.enable_cloudtrail ? 1 : 0
  
  name                         = "${local.name_prefix}-cloudtrail"
  s3_bucket_name              = aws_s3_bucket.cloudtrail[0].bucket
  s3_key_prefix               = "AWSLogs"
  include_global_service_events = true
  is_multi_region_trail        = true
  enable_logging               = true
  
  # KMS encryption for CloudTrail logs
  kms_key_id = aws_kms_key.cloudtrail[0].arn
  
  event_selector {
    read_write_type           = "All"
    include_management_events = true
    
    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::*/*"]
    }
    
    data_resource {
      type   = "AWS::DynamoDB::Table"
      values = ["*"]
    }
  }
  
  tags = local.common_tags
}

# S3 bucket for CloudTrail logs
resource "aws_s3_bucket" "cloudtrail" {
  count = var.enable_cloudtrail ? 1 : 0
  
  bucket        = "${local.name_prefix}-cloudtrail-${random_id.cloudtrail_suffix[0].hex}"
  force_destroy = var.environment != "production"
  
  tags = merge(local.common_tags, {
    Purpose = "audit-logging"
  })
}

# Random suffix for CloudTrail bucket
resource "random_id" "cloudtrail_suffix" {
  count = var.enable_cloudtrail ? 1 : 0
  
  byte_length = 4
}

# KMS key for CloudTrail encryption
resource "aws_kms_key" "cloudtrail" {
  count = var.enable_cloudtrail ? 1 : 0
  
  description             = "KMS key for CloudTrail encryption - ${local.name_prefix}"
  deletion_window_in_days = var.environment == "production" ? 30 : 7
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowCloudTrailAccess"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action = [
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Service = "cloudtrail-encryption"
  })
}

# CloudTrail bucket policy
resource "aws_s3_bucket_policy" "cloudtrail" {
  count = var.enable_cloudtrail ? 1 : 0
  
  bucket = aws_s3_bucket.cloudtrail[0].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.cloudtrail[0].arn
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cloudtrail[0].arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}

# ============================================================================
# DATA SOURCES
# ============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}