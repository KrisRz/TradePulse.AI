# TradePulse.AI - Monitoring Module Variables
# Professional variable definitions for monitoring resources

variable "environment" {
  description = "Environment name (production/staging)"
  type        = string
}

variable "deployment_id" {
  description = "Unique deployment identifier"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

# ============================================================================
# LAMBDA MONITORING CONFIGURATION
# ============================================================================

variable "lambda_functions" {
  description = "Map of Lambda function names to monitor"
  type        = map(string)
  default     = {}
}

variable "lambda_error_rate_threshold" {
  description = "Threshold for Lambda error rate alarm (percentage)"
  type        = number
  default     = 5.0
  
  validation {
    condition     = var.lambda_error_rate_threshold >= 0 && var.lambda_error_rate_threshold <= 100
    error_message = "Lambda error rate threshold must be between 0 and 100."
  }
}

variable "lambda_duration_threshold_ms" {
  description = "Threshold for Lambda duration alarm in milliseconds"
  type        = number
  default     = 30000
  
  validation {
    condition     = var.lambda_duration_threshold_ms > 0
    error_message = "Lambda duration threshold must be positive."
  }
}

variable "lambda_concurrent_executions_threshold" {
  description = "Threshold for Lambda concurrent executions alarm"
  type        = number
  default     = 100
  
  validation {
    condition     = var.lambda_concurrent_executions_threshold > 0
    error_message = "Lambda concurrent executions threshold must be positive."
  }
}

# ============================================================================
# API GATEWAY MONITORING CONFIGURATION
# ============================================================================

variable "api_gateway_id" {
  description = "API Gateway ID to monitor (leave empty to skip API Gateway monitoring)"
  type        = string
  default     = ""
}

variable "api_gateway_4xx_threshold" {
  description = "Threshold for API Gateway 4XX errors alarm"
  type        = number
  default     = 50
}

variable "api_gateway_5xx_threshold" {
  description = "Threshold for API Gateway 5XX errors alarm"
  type        = number
  default     = 5
}

variable "api_gateway_latency_threshold_ms" {
  description = "Threshold for API Gateway latency alarm in milliseconds"
  type        = number
  default     = 5000
}

# ============================================================================
# DYNAMODB MONITORING CONFIGURATION
# ============================================================================

variable "dynamodb_table_names" {
  description = "Map of DynamoDB table identifiers to actual table names"
  type        = map(string)
  default     = {}
}

variable "dynamodb_read_capacity_threshold" {
  description = "Threshold for DynamoDB read capacity alarm"
  type        = number
  default     = 80
}

variable "dynamodb_write_capacity_threshold" {
  description = "Threshold for DynamoDB write capacity alarm"
  type        = number
  default     = 80
}

# ============================================================================
# ALERTING CONFIGURATION
# ============================================================================

variable "alert_email_addresses" {
  description = "List of email addresses to receive alerts"
  type        = list(string)
  default     = []
  
  validation {
    condition = alltrue([
      for email in var.alert_email_addresses : can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", email))
    ])
    error_message = "All email addresses must be valid."
  }
}

variable "critical_alert_email_addresses" {
  description = "List of email addresses to receive critical alerts (production only)"
  type        = list(string)
  default     = []
  
  validation {
    condition = alltrue([
      for email in var.critical_alert_email_addresses : can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", email))
    ])
    error_message = "All critical alert email addresses must be valid."
  }
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications (leave empty to disable Slack notifications)"
  type        = string
  default     = ""
  sensitive   = true
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

variable "log_retention_days" {
  description = "Retention period for CloudWatch logs in days"
  type        = number
  default     = 30
  
  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

# ============================================================================
# ADVANCED MONITORING FEATURES
# ============================================================================

variable "enable_performance_monitoring" {
  description = "Enable advanced performance monitoring and dashboards"
  type        = bool
  default     = true
}

variable "enable_custom_metrics" {
  description = "Enable custom application metrics collection"
  type        = bool
  default     = true
}

variable "enable_business_metrics" {
  description = "Enable business-specific metrics and alarms"
  type        = bool
  default     = true
}

# ============================================================================
# CUSTOM BUSINESS METRICS THRESHOLDS
# ============================================================================

variable "trading_signals_min_threshold" {
  description = "Minimum number of trading signals that should be generated per 15-minute period"
  type        = number
  default     = 5
  
  validation {
    condition     = var.trading_signals_min_threshold >= 0
    error_message = "Trading signals minimum threshold must be non-negative."
  }
}

variable "application_error_threshold" {
  description = "Threshold for application-level errors per 5-minute period"
  type        = number
  default     = 10
  
  validation {
    condition     = var.application_error_threshold >= 0
    error_message = "Application error threshold must be non-negative."
  }
}

# ============================================================================
# COST OPTIMIZATION
# ============================================================================

variable "enable_detailed_monitoring" {
  description = "Enable detailed (1-minute) CloudWatch monitoring (additional cost)"
  type        = bool
  default     = false
}

variable "dashboard_refresh_interval" {
  description = "Dashboard refresh interval in seconds"
  type        = number
  default     = 300
  
  validation {
    condition     = var.dashboard_refresh_interval >= 60
    error_message = "Dashboard refresh interval must be at least 60 seconds."
  }
}

# ============================================================================
# TAGS
# ============================================================================

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}