# TradePulse.AI - Security Module Variables

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
# SECRETS CONFIGURATION
# ============================================================================

variable "secrets_config" {
  description = "Configuration for secrets to be stored in AWS Secrets Manager"
  type        = map(string)
  sensitive   = true
  default     = {}
}

# ============================================================================
# SSL/TLS CERTIFICATE CONFIGURATION
# ============================================================================

variable "domain_name" {
  description = "Domain name for SSL certificate (leave empty to skip certificate creation)"
  type        = string
  default     = ""
}

variable "manage_dns" {
  description = "Whether to manage DNS records for certificate validation"
  type        = bool
  default     = false
}

# ============================================================================
# WAF CONFIGURATION
# ============================================================================

variable "enable_waf" {
  description = "Enable AWS WAF Web ACL"
  type        = bool
  default     = true
}

variable "rate_limit_per_ip" {
  description = "Rate limit per IP address (requests per 5 minutes)"
  type        = number
  default     = 2000
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access resources"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allowed_countries" {
  description = "List of country codes allowed to access resources (empty = allow all)"
  type        = list(string)
  default     = []
}

variable "waf_log_retention_days" {
  description = "Retention period for WAF logs in days"
  type        = number
  default     = 30
}

# ============================================================================
# SECURITY GROUP CONFIGURATION
# ============================================================================

variable "vpc_id" {
  description = "VPC ID for security groups (optional)"
  type        = string
  default     = ""
}

variable "create_external_api_sg" {
  description = "Create security group for external API access"
  type        = bool
  default     = false
}

variable "allow_http" {
  description = "Allow HTTP traffic (in addition to HTTPS)"
  type        = bool
  default     = false
}

# ============================================================================
# ENCRYPTION CONFIGURATION
# ============================================================================

variable "create_application_kms_key" {
  description = "Create a KMS key for application-level encryption"
  type        = bool
  default     = true
}

variable "lambda_role_arn" {
  description = "ARN of Lambda execution role for KMS key access"
  type        = string
  default     = ""
}

# ============================================================================
# AUDIT LOGGING CONFIGURATION
# ============================================================================

variable "enable_cloudtrail" {
  description = "Enable CloudTrail for audit logging"
  type        = bool
  default     = true
}

# ============================================================================
# TAGS
# ============================================================================

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}