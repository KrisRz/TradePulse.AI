# TradePulse.AI - Production Environment Variables
# Professional Terraform configuration with comprehensive validation

# ============================================================================
# BASIC CONFIGURATION
# ============================================================================

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-west-2"
  
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "AWS region must be in correct format (e.g., eu-west-2)."
  }
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
  
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "tradepulse"
  
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*[a-z0-9]$", var.project_name))
    error_message = "Project name must start with a letter, contain only lowercase letters, numbers, and hyphens."
  }
}

variable "domain_name" {
  description = "Custom domain name for the application (optional)"
  type        = string
  default     = ""
}

# ============================================================================
# NETWORKING CONFIGURATION
# ============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access the infrastructure"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_vpc" {
  description = "Enable VPC for Lambda functions"
  type        = bool
  default     = true
}

variable "enable_vpc_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

variable "enable_waf" {
  description = "Enable AWS WAF for API Gateway"
  type        = bool
  default     = true
}

variable "api_rate_limit" {
  description = "API rate limit per IP (requests per 5 minutes)"
  type        = number
  default     = 2000
  
  validation {
    condition     = var.api_rate_limit > 0 && var.api_rate_limit <= 10000
    error_message = "API rate limit must be between 1 and 10000."
  }
}

variable "cors_allowed_origins" {
  description = "List of allowed CORS origins"
  type        = list(string)
  default     = ["*"]
}

# ============================================================================
# SECRETS MANAGEMENT
# ============================================================================

variable "binance_api_key" {
  description = "Binance API Key (will be stored in AWS Secrets Manager)"
  type        = string
  sensitive   = true
  
  validation {
    condition     = length(var.binance_api_key) > 10
    error_message = "Binance API key must be provided and have more than 10 characters."
  }
}

variable "binance_secret_key" {
  description = "Binance Secret Key (will be stored in AWS Secrets Manager)"
  type        = string
  sensitive   = true
  
  validation {
    condition     = length(var.binance_secret_key) > 10
    error_message = "Binance secret key must be provided and have more than 10 characters."
  }
}

variable "jwt_secret_key" {
  description = "JWT Secret Key for authentication (will be stored in AWS Secrets Manager)"
  type        = string
  sensitive   = true
  
  validation {
    condition     = length(var.jwt_secret_key) >= 32
    error_message = "JWT secret key must be at least 32 characters long for security."
  }
}

# ============================================================================
# COMPUTE CONFIGURATION
# ============================================================================

variable "lambda_memory_size" {
  description = "Memory size for standard Lambda functions (MB)"
  type        = number
  default     = 1024
  
  validation {
    condition = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240 && (
      var.lambda_memory_size == 128 ||
      (var.lambda_memory_size >= 512 && var.lambda_memory_size % 64 == 0)
    )
    error_message = "Lambda memory must be 128 MB or between 512-10240 MB in 64 MB increments."
  }
}

variable "ai_lambda_memory_size" {
  description = "Memory size for AI/ML Lambda functions (MB)"
  type        = number
  default     = 2048
  
  validation {
    condition = var.ai_lambda_memory_size >= 512 && var.ai_lambda_memory_size <= 10240 && var.ai_lambda_memory_size % 64 == 0
    error_message = "AI Lambda memory must be between 512-10240 MB in 64 MB increments."
  }
}

variable "ml_lambda_memory_size" {
  description = "Memory size for ML training Lambda functions (MB)"
  type        = number
  default     = 4096
  
  validation {
    condition = var.ml_lambda_memory_size >= 1024 && var.ml_lambda_memory_size <= 10240 && var.ml_lambda_memory_size % 64 == 0
    error_message = "ML Lambda memory must be between 1024-10240 MB in 64 MB increments."
  }
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions (seconds)"
  type        = number
  default     = 30
  
  validation {
    condition     = var.lambda_timeout >= 3 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 3 and 900 seconds."
  }
}

variable "max_lambda_concurrency" {
  description = "Maximum concurrent Lambda executions"
  type        = number
  default     = 100
  
  validation {
    condition     = var.max_lambda_concurrency >= 10 && var.max_lambda_concurrency <= 1000
    error_message = "Max Lambda concurrency must be between 10 and 1000."
  }
}

# ============================================================================
# API GATEWAY CONFIGURATION
# ============================================================================

variable "api_throttle_burst" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 2000
}

variable "api_throttle_rate" {
  description = "API Gateway throttle rate limit (requests per second)"
  type        = number
  default     = 1000
}

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

variable "enable_global_tables" {
  description = "Enable DynamoDB Global Tables for multi-region replication"
  type        = bool
  default     = false
}

variable "dynamodb_read_capacity" {
  description = "DynamoDB read capacity units (only used with provisioned billing)"
  type        = number
  default     = 10
}

variable "dynamodb_write_capacity" {
  description = "DynamoDB write capacity units (only used with provisioned billing)"
  type        = number
  default     = 10
}

variable "enable_point_in_time_recovery" {
  description = "Enable Point-in-Time Recovery for DynamoDB tables"
  type        = bool
  default     = true
}

# ============================================================================
# STORAGE CONFIGURATION
# ============================================================================

variable "s3_lifecycle_rules" {
  description = "S3 lifecycle management rules"
  type = list(object({
    id                          = string
    status                      = string
    transition_days            = number
    transition_storage_class    = string
    expiration_days            = optional(number)
  }))
  default = [
    {
      id                       = "standard_to_ia"
      status                   = "Enabled"
      transition_days          = 30
      transition_storage_class = "STANDARD_IA"
    },
    {
      id                       = "ia_to_glacier"
      status                   = "Enabled"
      transition_days          = 90
      transition_storage_class = "GLACIER"
    }
  ]
}

# ============================================================================
# BACKUP AND RECOVERY
# ============================================================================

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
  
  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 365
    error_message = "Backup retention days must be between 1 and 365."
  }
}

variable "enable_cross_region_backup" {
  description = "Enable cross-region backup for disaster recovery"
  type        = bool
  default     = true
}

# ============================================================================
# MONITORING CONFIGURATION
# ============================================================================

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
  
  validation {
    condition = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
  
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL."
  }
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "enable_xray_tracing" {
  description = "Enable AWS X-Ray distributed tracing"
  type        = bool
  default     = true
}

# ============================================================================
# ALERTING CONFIGURATION
# ============================================================================

variable "alert_email_addresses" {
  description = "List of email addresses for general alerts"
  type        = list(string)
  default     = ["admin@tradepulse.ai"]
  
  validation {
    condition = alltrue([
      for email in var.alert_email_addresses : can(regex("^[^@]+@[^@]+\\.[^@]+$", email))
    ])
    error_message = "All email addresses must be valid."
  }
}

variable "trading_alert_email_addresses" {
  description = "List of email addresses for trading alerts"
  type        = list(string)
  default     = ["trading@tradepulse.ai"]
  
  validation {
    condition = alltrue([
      for email in var.trading_alert_email_addresses : can(regex("^[^@]+@[^@]+\\.[^@]+$", email))
    ])
    error_message = "All trading email addresses must be valid."
  }
}

variable "critical_alert_email_addresses" {
  description = "List of email addresses for critical alerts"
  type        = list(string)
  default     = ["critical@tradepulse.ai"]
  
  validation {
    condition = alltrue([
      for email in var.critical_alert_email_addresses : can(regex("^[^@]+@[^@]+\\.[^@]+$", email))
    ])
    error_message = "All critical email addresses must be valid."
  }
}

variable "discord_webhook_url" {
  description = "Discord webhook URL for notifications (optional)"
  type        = string
  default     = ""
}

variable "telegram_bot_token" {
  description = "Telegram bot token for notifications (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "monthly_cost_alert_threshold" {
  description = "Monthly cost alert threshold in USD"
  type        = number
  default     = 500
  
  validation {
    condition     = var.monthly_cost_alert_threshold > 0
    error_message = "Monthly cost alert threshold must be greater than 0."
  }
}

variable "cost_alert_email" {
  description = "Email address for cost alerts"
  type        = string
  default     = "billing@tradepulse.ai"
  
  validation {
    condition     = can(regex("^[^@]+@[^@]+\\.[^@]+$", var.cost_alert_email))
    error_message = "Cost alert email must be a valid email address."
  }
}

# ============================================================================
# TRADING CONFIGURATION
# ============================================================================

variable "supported_symbols" {
  description = "List of cryptocurrency symbols to support"
  type        = list(string)
  default = [
    "BTCUSDT",
    "ETHUSDT",
    "ADAUSDT",
    "SOLUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "AVAXUSDT"
  ]
  
  validation {
    condition = alltrue([
      for symbol in var.supported_symbols : can(regex("^[A-Z]{3,10}USDT$", symbol))
    ])
    error_message = "All symbols must end with USDT and contain only uppercase letters."
  }
}

variable "trading_intervals" {
  description = "List of trading time intervals"
  type        = list(string)
  default     = ["1m", "5m", "15m", "1h", "4h", "1d"]
  
  validation {
    condition = alltrue([
      for interval in var.trading_intervals : contains(["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"], interval)
    ])
    error_message = "Trading intervals must be valid Binance intervals."
  }
}

variable "enable_live_trading" {
  description = "Enable live trading (CAUTION: This will trade real money)"
  type        = bool
  default     = false
}

variable "max_position_size_usd" {
  description = "Maximum position size in USD"
  type        = number
  default     = 1000
  
  validation {
    condition     = var.max_position_size_usd > 0 && var.max_position_size_usd <= 100000
    error_message = "Max position size must be between 1 and 100000 USD."
  }
}

variable "risk_management_enabled" {
  description = "Enable risk management features"
  type        = bool
  default     = true
}

# ============================================================================
# CLOUDFRONT CONFIGURATION
# ============================================================================

variable "cloudfront_price_class" {
  description = "CloudFront distribution price class"
  type        = string
  default     = "PriceClass_100"
  
  validation {
    condition = contains([
      "PriceClass_All",
      "PriceClass_200", 
      "PriceClass_100"
    ], var.cloudfront_price_class)
    error_message = "CloudFront price class must be PriceClass_All, PriceClass_200, or PriceClass_100."
  }
}

# ============================================================================
# EVENTBRIDGE CONFIGURATION
# ============================================================================

variable "eventbridge_schedules" {
  description = "EventBridge schedule rules configuration"
  type = map(object({
    description         = string
    schedule_expression = string
    target_function    = string
    input              = optional(string, "{}")
  }))
  default = {
    data_collection = {
      description         = "Collect market data every minute"
      schedule_expression = "rate(1 minute)"
      target_function    = "data_collector"
      input              = jsonencode({
        action = "collect_market_data"
        symbols = ["BTCUSDT", "ETHUSDT"]
      })
    }
    
    health_check = {
      description         = "Health check every 5 minutes"
      schedule_expression = "rate(5 minutes)"
      target_function    = "health_monitor"
      input              = jsonencode({
        action = "system_health_check"
      })
    }
    
    model_update = {
      description         = "Update ML models daily"
      schedule_expression = "rate(24 hours)"
      target_function    = "ml_model_updater"
      input              = jsonencode({
        action = "update_models"
      })
    }
    
    position_check = {
      description         = "Check positions every 30 seconds"
      schedule_expression = "rate(30 seconds)"
      target_function    = "position_monitor"
      input              = jsonencode({
        action = "monitor_positions"
      })
    }
  }
}

# ============================================================================
# FEATURE FLAGS
# ============================================================================

variable "enable_advanced_analytics" {
  description = "Enable advanced analytics features"
  type        = bool
  default     = true
}

variable "enable_ml_continuous_learning" {
  description = "Enable continuous ML model learning"
  type        = bool
  default     = true
}

variable "enable_social_trading" {
  description = "Enable social trading features"
  type        = bool
  default     = false
}

variable "enable_portfolio_showcase" {
  description = "Enable portfolio showcase features"
  type        = bool
  default     = true
}

variable "enable_api_versioning" {
  description = "Enable API versioning support"
  type        = bool
  default     = true
}

variable "enable_debug_mode" {
  description = "Enable debug mode (only for development)"
  type        = bool
  default     = false
}

variable "enable_performance_testing" {
  description = "Enable performance testing features"
  type        = bool
  default     = false
}

# ============================================================================
# COMPLIANCE AND GOVERNANCE
# ============================================================================

variable "enable_compliance_logging" {
  description = "Enable compliance and audit logging"
  type        = bool
  default     = true
}

variable "data_residency_region" {
  description = "Primary region for data residency compliance"
  type        = string
  default     = "eu-west-2"
}

variable "enable_encryption_at_rest" {
  description = "Enable encryption at rest for all storage"
  type        = bool
  default     = true
}

variable "enable_encryption_in_transit" {
  description = "Enable encryption in transit for all communications"
  type        = bool
  default     = true
}

# ============================================================================
# RESOURCE TAGGING
# ============================================================================

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default = {
    "Owner"           = "TradePulse-AI-Team"
    "Project"         = "AI-Trading-Platform"
    "CostOptimized"   = "true"
    "BackupEnabled"   = "true"
    "MonitoringLevel" = "comprehensive"
  }
}