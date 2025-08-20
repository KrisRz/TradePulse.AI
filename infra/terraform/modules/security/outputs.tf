# TradePulse.AI - Security Module Outputs
# Professional output definitions for security resources

# ============================================================================
# SECRETS MANAGER OUTPUTS
# ============================================================================

output "secrets_manager_secret_arns" {
  description = "ARNs of all Secrets Manager secrets"
  value       = { for k, secret in aws_secretsmanager_secret.secrets : k => secret.arn }
  sensitive   = true
}

output "secrets_manager_secret_ids" {
  description = "IDs of all Secrets Manager secrets"
  value       = { for k, secret in aws_secretsmanager_secret.secrets : k => secret.id }
  sensitive   = true
}

output "secrets_access_policy_arn" {
  description = "ARN of the IAM policy for accessing secrets"
  value       = aws_iam_policy.secrets_access.arn
}

# ============================================================================
# SSL/TLS CERTIFICATE OUTPUTS
# ============================================================================

output "ssl_certificate_arn" {
  description = "ARN of the SSL certificate (if created)"
  value       = var.domain_name != "" ? aws_acm_certificate.main[0].arn : ""
}

output "ssl_certificate_id" {
  description = "ID of the SSL certificate (if created)"
  value       = var.domain_name != "" ? aws_acm_certificate.main[0].id : ""
}

output "ssl_certificate_domain_name" {
  description = "Domain name of the SSL certificate"
  value       = var.domain_name
}

output "ssl_certificate_status" {
  description = "Status of the SSL certificate"
  value       = var.domain_name != "" ? aws_acm_certificate.main[0].status : "not_created"
}

output "ssl_certificate_validation_arn" {
  description = "ARN of the validated SSL certificate (if DNS validation is managed)"
  value       = var.domain_name != "" && var.manage_dns ? aws_acm_certificate_validation.main[0].certificate_arn : ""
}

# ============================================================================
# AWS WAF OUTPUTS
# ============================================================================

output "waf_web_acl_arn" {
  description = "ARN of the WAF Web ACL (if enabled)"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].arn : ""
}

output "waf_web_acl_id" {
  description = "ID of the WAF Web ACL (if enabled)"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].id : ""
}

output "waf_web_acl_name" {
  description = "Name of the WAF Web ACL"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].name : ""
}

output "waf_ip_set_arn" {
  description = "ARN of the WAF IP set for allowed IPs (if created)"
  value       = var.enable_waf && length(var.allowed_cidr_blocks) > 0 && var.allowed_cidr_blocks != ["0.0.0.0/0"] ? aws_wafv2_ip_set.allowed_ips[0].arn : ""
}

output "waf_log_group_name" {
  description = "Name of the CloudWatch log group for WAF logs"
  value       = var.enable_waf ? aws_cloudwatch_log_group.waf[0].name : ""
}

output "waf_log_group_arn" {
  description = "ARN of the CloudWatch log group for WAF logs"
  value       = var.enable_waf ? aws_cloudwatch_log_group.waf[0].arn : ""
}

# ============================================================================
# SECURITY GROUP OUTPUTS
# ============================================================================

output "external_api_security_group_id" {
  description = "ID of the external API security group (if created)"
  value       = var.create_external_api_sg ? aws_security_group.external_api[0].id : ""
}

output "external_api_security_group_arn" {
  description = "ARN of the external API security group (if created)"
  value       = var.create_external_api_sg ? aws_security_group.external_api[0].arn : ""
}

# ============================================================================
# KMS ENCRYPTION OUTPUTS
# ============================================================================

output "application_kms_key_arn" {
  description = "ARN of the application KMS key (if created)"
  value       = var.create_application_kms_key ? aws_kms_key.application[0].arn : ""
}

output "application_kms_key_id" {
  description = "ID of the application KMS key (if created)"
  value       = var.create_application_kms_key ? aws_kms_key.application[0].key_id : ""
}

output "application_kms_key_alias" {
  description = "Alias of the application KMS key (if created)"
  value       = var.create_application_kms_key ? aws_kms_alias.application[0].name : ""
}

output "cloudtrail_kms_key_arn" {
  description = "ARN of the CloudTrail KMS key (if enabled)"
  value       = var.enable_cloudtrail ? aws_kms_key.cloudtrail[0].arn : ""
}

output "cloudtrail_kms_key_id" {
  description = "ID of the CloudTrail KMS key (if enabled)"
  value       = var.enable_cloudtrail ? aws_kms_key.cloudtrail[0].key_id : ""
}

# ============================================================================
# CLOUDTRAIL AUDIT LOGGING OUTPUTS
# ============================================================================

output "cloudtrail_arn" {
  description = "ARN of the CloudTrail (if enabled)"
  value       = var.enable_cloudtrail ? aws_cloudtrail.main[0].arn : ""
}

output "cloudtrail_id" {
  description = "ID of the CloudTrail (if enabled)"
  value       = var.enable_cloudtrail ? aws_cloudtrail.main[0].id : ""
}

output "cloudtrail_name" {
  description = "Name of the CloudTrail"
  value       = var.enable_cloudtrail ? aws_cloudtrail.main[0].name : ""
}

output "cloudtrail_bucket_name" {
  description = "Name of the S3 bucket for CloudTrail logs"
  value       = var.enable_cloudtrail ? aws_s3_bucket.cloudtrail[0].bucket : ""
}

output "cloudtrail_bucket_arn" {
  description = "ARN of the S3 bucket for CloudTrail logs"
  value       = var.enable_cloudtrail ? aws_s3_bucket.cloudtrail[0].arn : ""
}

# ============================================================================
# SECURITY CONFIGURATION SUMMARY
# ============================================================================

output "security_config_summary" {
  description = "Summary of security configuration"
  value = {
    secrets_manager = {
      enabled       = length(var.secrets_config) > 0
      secrets_count = length(var.secrets_config)
    }
    
    ssl_certificates = {
      enabled     = var.domain_name != ""
      domain_name = var.domain_name
      managed_dns = var.manage_dns
    }
    
    waf_protection = {
      enabled                = var.enable_waf
      rate_limit_per_ip     = var.rate_limit_per_ip
      geo_restrictions      = length(var.allowed_countries) > 0
      ip_whitelist          = length(var.allowed_cidr_blocks) > 0 && var.allowed_cidr_blocks != ["0.0.0.0/0"]
    }
    
    encryption = {
      application_kms_key = var.create_application_kms_key
      cloudtrail_kms_key = var.enable_cloudtrail
    }
    
    audit_logging = {
      cloudtrail_enabled = var.enable_cloudtrail
      waf_logging       = var.enable_waf
    }
    
    access_control = {
      external_api_sg = var.create_external_api_sg
      secrets_policy  = true
    }
  }
}

# ============================================================================
# COMPLIANCE AND MONITORING OUTPUTS
# ============================================================================

output "compliance_info" {
  description = "Security compliance information"
  value = {
    encryption_at_rest = {
      secrets_manager = "AWS managed encryption"
      s3_cloudtrail   = var.enable_cloudtrail ? "KMS encryption enabled" : "not_applicable"
      application_data = var.create_application_kms_key ? "Customer managed KMS key" : "AWS managed keys"
    }
    
    encryption_in_transit = {
      ssl_certificates = var.domain_name != "" ? "ACM SSL certificate configured" : "manual_ssl_required"
      waf_protection   = var.enable_waf ? "WAF enabled with HTTPS enforcement" : "disabled"
    }
    
    access_logging = {
      cloudtrail    = var.enable_cloudtrail ? "Multi-region trail with data events" : "disabled"
      waf_logs      = var.enable_waf ? "CloudWatch logs enabled" : "not_applicable"
      vpc_flow_logs = "configured_in_networking_module"
    }
    
    network_security = {
      security_groups     = "Lambda and optional external API security groups"
      network_acls        = "configured_in_networking_module"
      vpc_endpoints       = "configured_in_networking_module"
      waf_protection      = var.enable_waf ? "Enabled with managed rule sets" : "disabled"
    }
    
    data_protection = {
      secrets_rotation    = "Manual rotation supported"
      backup_retention    = var.environment == "production" ? "30 days" : "7 days"
      deletion_protection = var.environment == "production" ? "30 days recovery window" : "7 days recovery window"
    }
  }
}

# ============================================================================
# COST INFORMATION
# ============================================================================

output "cost_factors" {
  description = "Security-related cost factors"
  value = {
    secrets_manager_secrets     = length(var.secrets_config)
    waf_web_acl                = var.enable_waf ? 1 : 0
    waf_rules_count            = var.enable_waf ? 5 + (length(var.allowed_countries) > 0 ? 1 : 0) + (length(var.allowed_cidr_blocks) > 0 && var.allowed_cidr_blocks != ["0.0.0.0/0"] ? 1 : 0) : 0
    kms_keys_count             = (var.create_application_kms_key ? 1 : 0) + (var.enable_cloudtrail ? 1 : 0)
    acm_certificates_count     = var.domain_name != "" ? 1 : 0
    cloudtrail_enabled         = var.enable_cloudtrail
    estimated_monthly_base_cost = {
      secrets_manager  = length(var.secrets_config) * 0.40  # ~$0.40/month per secret
      waf_web_acl      = var.enable_waf ? 1.00 : 0          # ~$1.00/month per Web ACL
      kms_keys         = ((var.create_application_kms_key ? 1 : 0) + (var.enable_cloudtrail ? 1 : 0)) * 1.00  # ~$1.00/month per key
      acm_certificates = 0  # ACM certificates are free
      cloudtrail       = var.enable_cloudtrail ? 2.00 : 0   # ~$2.00/month base cost
    }
  }
}

# ============================================================================
# INTEGRATION OUTPUTS FOR OTHER MODULES
# ============================================================================

output "integration_info" {
  description = "Information for integration with other modules"
  value = {
    # For Lambda functions
    secrets_access_policy_arn = aws_iam_policy.secrets_access.arn
    application_kms_key_arn   = var.create_application_kms_key ? aws_kms_key.application[0].arn : ""
    
    # For CloudFront
    waf_web_acl_arn          = var.enable_waf ? aws_wafv2_web_acl.main[0].arn : ""
    ssl_certificate_arn      = var.domain_name != "" ? aws_acm_certificate.main[0].arn : ""
    
    # For API Gateway
    external_api_sg_id       = var.create_external_api_sg ? aws_security_group.external_api[0].id : ""
    
    # For monitoring
    waf_log_group_name       = var.enable_waf ? aws_cloudwatch_log_group.waf[0].name : ""
    cloudtrail_log_bucket    = var.enable_cloudtrail ? aws_s3_bucket.cloudtrail[0].bucket : ""
  }
}