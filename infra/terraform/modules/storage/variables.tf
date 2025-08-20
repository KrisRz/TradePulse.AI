# TradePulse.AI - Storage Module Variables
# Professional variable definitions for storage resources

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
# DYNAMODB CONFIGURATION
# ============================================================================

variable "tables_config" {
  description = "Configuration for DynamoDB tables"
  type = map(object({
    hash_key           = string
    range_key          = optional(string)
    billing_mode       = string
    enable_encryption  = bool
    enable_pitr        = bool
    enable_streams     = bool
    ttl_attribute      = optional(string)
    global_tables      = optional(bool, false)
    
    # GSI configuration
    gsi_attributes = optional(list(object({
      name = string
      type = string
    })), [])
    
    global_secondary_indexes = optional(list(object({
      name            = string
      hash_key        = string
      range_key       = optional(string)
      projection_type = string
      non_key_attributes = optional(list(string), [])
    })), [])
    
    local_secondary_indexes = optional(list(object({
      name            = string
      range_key       = string
      projection_type = string
    })), [])
  }))
}

# ============================================================================
# S3 CONFIGURATION
# ============================================================================

variable "s3_buckets" {
  description = "Configuration for S3 buckets"
  type = map(object({
    purpose           = string
    enable_versioning = bool
    enable_encryption = bool
    enable_cors       = bool
    lifecycle_rules = list(object({
      id                       = string
      status                   = string
      transition_days          = number
      transition_storage_class = string
      expiration_days          = optional(number)
    }))
  }))
}

# ============================================================================
# BACKUP CONFIGURATION
# ============================================================================

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

variable "enable_cross_region_backup" {
  description = "Enable cross-region backup for disaster recovery"
  type        = bool
  default     = false
}

variable "enable_point_in_time_recovery" {
  description = "Enable Point-in-Time Recovery for DynamoDB tables"
  type        = bool
  default     = true
}

# ============================================================================
# EXTERNAL DEPENDENCIES
# ============================================================================

variable "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution for S3 bucket policy"
  type        = string
  default     = ""
}

# ============================================================================
# TAGS
# ============================================================================

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Optional explicit naming to adopt existing resources
variable "explicit_table_names" {
  description = "Explicit DynamoDB table names keyed by tables_config keys"
  type        = map(string)
  default     = {}
}

variable "explicit_bucket_names" {
  description = "Explicit S3 bucket names keyed by s3_buckets keys"
  type        = map(string)
  default     = {}
}