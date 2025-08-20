# TradePulse.AI - Production Environment Outputs
# Professional output definitions for integration and monitoring

# ============================================================================
# DEPLOYMENT INFORMATION
# ============================================================================

output "deployment_id" {
  description = "Unique deployment identifier"
  value       = local.deployment_id
}

output "environment" {
  description = "Deployment environment"
  value       = var.environment
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}

output "deployment_timestamp" {
  description = "Timestamp of deployment"
  value       = timestamp()
}

# ============================================================================
# NETWORKING OUTPUTS
# ============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.networking.vpc_id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = module.networking.vpc_cidr
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.networking.private_subnet_ids
}

output "availability_zones" {
  description = "Availability zones used"
  value       = data.aws_availability_zones.available.names
}

# ============================================================================
# API GATEWAY OUTPUTS
# ============================================================================

output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = module.compute.api_gateway_id
}

output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = module.compute.api_gateway_url
}

output "api_gateway_domain" {
  description = "Domain name of the API Gateway"
  value       = module.compute.api_gateway_domain
}

output "api_endpoint" {
  description = "Main API endpoint URL"
  value       = module.compute.api_gateway_url
  sensitive   = false
}

output "api_stage" {
  description = "API Gateway deployment stage"
  value       = "$default"
}

# Custom domain outputs (if configured)
output "custom_api_domain" {
  description = "Custom domain for API (if configured)"
  value       = var.domain_name != "" ? "https://api.${var.domain_name}" : ""
}

# ============================================================================
# LAMBDA FUNCTION OUTPUTS
# ============================================================================

output "lambda_function_names" {
  description = "Names of all Lambda functions"
  value       = module.compute.lambda_function_names
}

output "lambda_function_arns" {
  description = "ARNs of all Lambda functions"
  value       = module.compute.lambda_function_arns
  sensitive   = true
}

output "lambda_function_urls" {
  description = "Function URLs for Lambda functions (if enabled)"
  value       = module.compute.lambda_function_urls
}

# Individual Lambda function outputs
output "backend_api_function_name" {
  description = "Name of the backend API Lambda function"
  value       = module.compute.lambda_function_names["backend_api"]
}

output "ai_signals_function_name" {
  description = "Name of the AI signals Lambda function"
  value       = module.compute.lambda_function_names["ai_signals"]
}

output "data_collector_function_name" {
  description = "Name of the data collector Lambda function"
  value       = module.compute.lambda_function_names["data_collector"]
}

# ============================================================================
# DYNAMODB OUTPUTS
# ============================================================================

output "dynamodb_table_names" {
  description = "Names of all DynamoDB tables"
  value       = module.storage.dynamodb_table_names
}

output "dynamodb_table_arns" {
  description = "ARNs of all DynamoDB tables"
  value       = module.storage.dynamodb_table_arns
  sensitive   = true
}

output "dynamodb_stream_arns" {
  description = "Stream ARNs for DynamoDB tables (where enabled)"
  value       = module.storage.dynamodb_stream_arns
  sensitive   = true
}

# Key table outputs
output "users_table_name" {
  description = "Name of the users DynamoDB table"
  value       = module.storage.dynamodb_table_names["users"]
}

output "positions_table_name" {
  description = "Name of the positions DynamoDB table"
  value       = module.storage.dynamodb_table_names["positions"]
}

output "signals_table_name" {
  description = "Name of the signals DynamoDB table"
  value       = module.storage.dynamodb_table_names["signals"]
}

# ============================================================================
# S3 BUCKET OUTPUTS
# ============================================================================

output "s3_bucket_names" {
  description = "Names of all S3 buckets"
  value       = module.storage.s3_bucket_names
}

output "s3_bucket_arns" {
  description = "ARNs of all S3 buckets"
  value       = module.storage.s3_bucket_arns
  sensitive   = true
}

output "s3_bucket_domains" {
  description = "Domain names of S3 buckets"
  value       = module.storage.s3_bucket_domains
}

# Individual bucket outputs
output "frontend_bucket_name" {
  description = "Name of the frontend S3 bucket"
  value       = module.storage.s3_bucket_names["frontend"]
}

output "data_bucket_name" {
  description = "Name of the data S3 bucket"
  value       = module.storage.s3_bucket_names["data"]
}

output "models_bucket_name" {
  description = "Name of the ML models S3 bucket"
  value       = module.storage.s3_bucket_names["models"]
}

# ============================================================================
# CLOUDFRONT OUTPUTS
# ============================================================================

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = module.compute.cloudfront_distribution_id
}

output "cloudfront_domain" {
  description = "Domain name of the CloudFront distribution"
  value       = module.compute.cloudfront_domain
}

output "cloudfront_url" {
  description = "URL of the CloudFront distribution"
  value       = "https://${module.compute.cloudfront_domain}"
}

# Custom domain for frontend (if configured)
output "custom_frontend_domain" {
  description = "Custom domain for frontend (if configured)"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : ""
}

# ============================================================================
# SECURITY OUTPUTS
# ============================================================================

output "certificate_arn" {
  description = "ARN of the SSL/TLS certificate (if custom domain configured)"
  value       = var.domain_name != "" ? module.security.certificate_arn : ""
  sensitive   = true
}

output "waf_web_acl_arn" {
  description = "ARN of the WAF Web ACL (if enabled)"
  value       = var.enable_waf ? module.security.waf_web_acl_arn : ""
  sensitive   = true
}

output "secrets_manager_arns" {
  description = "ARNs of Secrets Manager secrets"
  value       = module.security.secrets_manager_arns
  sensitive   = true
}

# Security groups
output "lambda_security_group_id" {
  description = "ID of the Lambda security group"
  value       = var.enable_vpc ? module.security.lambda_security_group_id : ""
}

# ============================================================================
# MONITORING OUTPUTS
# ============================================================================

output "cloudwatch_log_groups" {
  description = "Names of CloudWatch log groups"
  value       = module.monitoring.cloudwatch_log_groups
}

output "sns_topic_arns" {
  description = "ARNs of SNS topics for alerts"
  value       = module.monitoring.sns_topic_arns
  sensitive   = true
}

output "cloudwatch_dashboard_url" {
  description = "URL of the CloudWatch dashboard"
  value       = module.monitoring.cloudwatch_dashboard_url
}

# ============================================================================
# EVENTBRIDGE OUTPUTS
# ============================================================================

output "eventbridge_rule_arns" {
  description = "ARNs of EventBridge rules"
  value       = module.compute.eventbridge_rule_arns
  sensitive   = true
}

output "eventbridge_bus_name" {
  description = "Name of the custom EventBridge bus (if created)"
  value       = module.compute.eventbridge_bus_name
}

# ============================================================================
# APPLICATION CONFIGURATION OUTPUTS
# ============================================================================

output "application_config" {
  description = "Key application configuration for external systems"
  value = {
    environment         = var.environment
    region             = var.aws_region
    api_endpoint       = module.compute.api_gateway_url
    frontend_url       = "https://${module.compute.cloudfront_domain}"
    supported_symbols  = var.supported_symbols
    trading_intervals  = var.trading_intervals
    live_trading_enabled = var.enable_live_trading
    features = {
      advanced_analytics    = var.enable_advanced_analytics
      ml_continuous_learning = var.enable_ml_continuous_learning
      social_trading       = var.enable_social_trading
      portfolio_showcase   = var.enable_portfolio_showcase
    }
  }
  sensitive = false
}

# ============================================================================
# COST TRACKING OUTPUTS
# ============================================================================

output "resource_count_summary" {
  description = "Summary of resources created for cost tracking"
  value = {
    lambda_functions    = length(module.compute.lambda_function_names)
    dynamodb_tables    = length(module.storage.dynamodb_table_names)
    s3_buckets         = length(module.storage.s3_bucket_names)
    api_gateways       = 1
    cloudfront_distributions = 1
    vpc_enabled        = var.enable_vpc
    waf_enabled        = var.enable_waf
    global_tables_enabled = var.enable_global_tables
  }
}

output "estimated_monthly_cost_factors" {
  description = "Key factors that influence monthly costs"
  value = {
    lambda_memory_total_mb = (
      var.lambda_memory_size * 4 +  # 4 standard functions
      var.ai_lambda_memory_size +
      var.ml_lambda_memory_size
    )
    api_throttle_settings = {
      burst_limit = var.api_throttle_burst
      rate_limit  = var.api_throttle_rate
    }
    storage_settings = {
      dynamodb_billing_mode = "PAY_PER_REQUEST"
      s3_lifecycle_enabled = length(var.s3_lifecycle_rules) > 0
      backup_retention_days = var.backup_retention_days
    }
    monitoring_level = {
      detailed_monitoring = var.enable_detailed_monitoring
      xray_tracing       = var.enable_xray_tracing
      log_retention_days = var.log_retention_days
    }
  }
}

# ============================================================================
# INTEGRATION OUTPUTS
# ============================================================================

output "integration_endpoints" {
  description = "Key endpoints for external integrations"
  value = {
    health_check    = "${module.compute.api_gateway_url}/health"
    api_docs       = "${module.compute.api_gateway_url}/docs"
    metrics        = "${module.compute.api_gateway_url}/metrics"
    webhook        = "${module.compute.api_gateway_url}/webhook"
  }
}

output "webhook_urls" {
  description = "Webhook URLs for external services"
  value = {
    binance_webhook = "${module.compute.api_gateway_url}/webhook/binance"
    trading_signals = "${module.compute.api_gateway_url}/webhook/signals"
    system_alerts   = "${module.compute.api_gateway_url}/webhook/alerts"
  }
}

# ============================================================================
# DEPLOYMENT SUMMARY
# ============================================================================

output "deployment_summary" {
  description = "Complete deployment summary"
  value = {
    status = "SUCCESS"
    timestamp = timestamp()
    environment = var.environment
    region = var.aws_region
    deployment_id = local.deployment_id
    
    # Key URLs
    api_url = module.compute.api_gateway_url
    frontend_url = "https://${module.compute.cloudfront_domain}"
    dashboard_url = module.monitoring.cloudwatch_dashboard_url
    
    # Resource counts
    resources_created = {
      lambda_functions = length(module.compute.lambda_function_names)
      dynamodb_tables = length(module.storage.dynamodb_table_names)
      s3_buckets = length(module.storage.s3_bucket_names)
      cloudwatch_alarms = length(module.monitoring.cloudwatch_alarms)
    }
    
    # Feature flags
    features_enabled = {
      live_trading = var.enable_live_trading
      vpc = var.enable_vpc
      waf = var.enable_waf
      xray_tracing = var.enable_xray_tracing
      advanced_analytics = var.enable_advanced_analytics
      ml_continuous_learning = var.enable_ml_continuous_learning
    }
    
    # Security
    security_features = {
      encryption_at_rest = var.enable_encryption_at_rest
      encryption_in_transit = var.enable_encryption_in_transit
      waf_enabled = var.enable_waf
      secrets_manager = true
      vpc_isolation = var.enable_vpc
    }
  }
}