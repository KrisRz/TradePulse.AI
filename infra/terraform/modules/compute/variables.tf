# TradePulse.AI - Compute Module Variables
# Professional variable definitions for serverless compute resources

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

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

# ============================================================================
# LAMBDA CONFIGURATION
# ============================================================================

variable "lambda_functions" {
  description = "Configuration for Lambda functions"
  type = map(object({
    filename         = string
    handler          = string
    runtime          = string
    memory_size      = number
    timeout          = number
    environment_vars = map(string)
    vpc_config = optional(object({
      subnet_ids         = list(string)
      security_group_ids = list(string)
    }))
  }))
}

# Optional explicit function names to adopt existing Lambdas
variable "explicit_function_names" {
  description = "Explicit Lambda function names keyed by lambda_functions keys"
  type        = map(string)
  default     = {}
}

variable "max_lambda_concurrency" {
  description = "Maximum concurrent Lambda executions"
  type        = number
  default     = 100
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
}

variable "enable_xray_tracing" {
  description = "Enable AWS X-Ray distributed tracing"
  type        = bool
  default     = true
}

# ============================================================================
# API GATEWAY CONFIGURATION
# ============================================================================

variable "api_gateway_config" {
  description = "API Gateway configuration"
  type = object({
    name            = string
    description     = string
    protocol_type   = string
    cors_enabled    = bool
    throttle_burst  = number
    throttle_rate   = number
    custom_domain   = optional(string)
    certificate_arn = optional(string)
  })
}

# ============================================================================
# EVENTBRIDGE CONFIGURATION
# ============================================================================

variable "eventbridge_rules" {
  description = "EventBridge schedule rules configuration"
  type = map(object({
    description         = string
    schedule_expression = string
    target_function    = string
    input              = optional(string, "{}")
  }))
  default = {}
}

# ============================================================================
# CLOUDFRONT CONFIGURATION
# ============================================================================

variable "cloudfront_config" {
  description = "CloudFront distribution configuration"
  type = object({
    frontend_bucket_id     = string
    frontend_bucket_domain = string
    api_domain            = string
    price_class           = string
    custom_domain         = optional(string)
    certificate_arn       = optional(string)
  })
}

# ============================================================================
# NETWORK DEPENDENCIES
# ============================================================================

variable "vpc_id" {
  description = "VPC ID for Lambda functions (optional)"
  type        = string
  default     = null
}

variable "public_subnet_ids" {
  description = "Public subnet IDs"
  type        = list(string)
  default     = []
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for Lambda functions"
  type        = list(string)
  default     = []
}

variable "lambda_security_group_id" {
  description = "Security group ID for Lambda functions"
  type        = string
  default     = null
}

# ============================================================================
# PERMISSION DEPENDENCIES
# ============================================================================

variable "secrets_manager_arns" {
  description = "List of Secrets Manager ARNs that Lambda can access"
  type        = list(string)
  default     = []
}

variable "dynamodb_table_arns" {
  description = "List of DynamoDB table ARNs that Lambda can access"
  type        = list(string)
  default     = []
}

variable "s3_bucket_arns" {
  description = "List of S3 bucket ARNs that Lambda can access"
  type        = list(string)
  default     = []
}

# ============================================================================
# TAGS
# ============================================================================

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}