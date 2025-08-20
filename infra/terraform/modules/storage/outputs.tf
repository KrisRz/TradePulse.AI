# TradePulse.AI - Storage Module Outputs
# Professional output definitions for storage resources

# ============================================================================
# DYNAMODB TABLE OUTPUTS
# ============================================================================

output "dynamodb_table_names" {
  description = "Names of all DynamoDB tables"
  value       = { for k, v in aws_dynamodb_table.tables : k => v.name }
}

output "dynamodb_table_arns" {
  description = "ARNs of all DynamoDB tables"
  value       = { for k, v in aws_dynamodb_table.tables : k => v.arn }
}

output "dynamodb_table_ids" {
  description = "IDs of all DynamoDB tables"
  value       = { for k, v in aws_dynamodb_table.tables : k => v.id }
}

output "dynamodb_stream_arns" {
  description = "Stream ARNs for DynamoDB tables (where enabled)"
  value = {
    for k, v in aws_dynamodb_table.tables : k => v.stream_arn
    if v.stream_arn != null
  }
}

output "dynamodb_stream_labels" {
  description = "Stream labels for DynamoDB tables (where enabled)"
  value = {
    for k, v in aws_dynamodb_table.tables : k => v.stream_label
    if v.stream_label != null
  }
}

output "dynamodb_table_endpoints" {
  description = "Table endpoints for DynamoDB tables"
  value       = { for k, v in aws_dynamodb_table.tables : k => "https://dynamodb.${data.aws_region.current.name}.amazonaws.com" }
}

# Individual table outputs for commonly referenced tables
output "users_table_name" {
  description = "Name of the users table"
  value       = try(aws_dynamodb_table.tables["users"].name, "")
}

output "positions_table_name" {
  description = "Name of the positions table"
  value       = try(aws_dynamodb_table.tables["positions"].name, "")
}

output "signals_table_name" {
  description = "Name of the signals table"
  value       = try(aws_dynamodb_table.tables["signals"].name, "")
}

output "live_candles_table_name" {
  description = "Name of the live candles table"
  value       = try(aws_dynamodb_table.tables["live_candles"].name, "")
}

output "virtual_portfolios_table_name" {
  description = "Name of the virtual portfolios table"
  value       = try(aws_dynamodb_table.tables["virtual_portfolios"].name, "")
}

# ============================================================================
# S3 BUCKET OUTPUTS
# ============================================================================

output "s3_bucket_names" {
  description = "Names of all S3 buckets"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.bucket }
}

output "s3_bucket_ids" {
  description = "IDs of all S3 buckets"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.id }
}

output "s3_bucket_arns" {
  description = "ARNs of all S3 buckets"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.arn }
}

output "s3_bucket_domains" {
  description = "Domain names of S3 buckets"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.bucket_domain_name }
}

output "s3_bucket_regional_domains" {
  description = "Regional domain names of S3 buckets"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.bucket_regional_domain_name }
}

output "s3_bucket_website_endpoints" {
  description = "Website endpoints for S3 buckets (where configured)"
  value = {
    for k, v in aws_s3_bucket_website_configuration.frontend : k => v.website_endpoint
  }
}

# Individual bucket outputs for commonly referenced buckets
output "frontend_bucket_name" {
  description = "Name of the frontend bucket"
  value       = try(aws_s3_bucket.buckets["frontend"].bucket, "")
}

output "data_bucket_name" {
  description = "Name of the data bucket"
  value       = try(aws_s3_bucket.buckets["data"].bucket, "")
}

output "models_bucket_name" {
  description = "Name of the models bucket"
  value       = try(aws_s3_bucket.buckets["models"].bucket, "")
}

output "backups_bucket_name" {
  description = "Name of the backups bucket"
  value       = try(aws_s3_bucket.buckets["backups"].bucket, "")
}

# ============================================================================
# KMS KEY OUTPUTS
# ============================================================================

output "dynamodb_kms_key_arn" {
  description = "ARN of the DynamoDB KMS key"
  value       = try(aws_kms_key.dynamodb[0].arn, "")
}

output "dynamodb_kms_key_id" {
  description = "ID of the DynamoDB KMS key"
  value       = try(aws_kms_key.dynamodb[0].key_id, "")
}

output "s3_kms_key_arn" {
  description = "ARN of the S3 KMS key"
  value       = try(aws_kms_key.s3[0].arn, "")
}

output "s3_kms_key_id" {
  description = "ID of the S3 KMS key"
  value       = try(aws_kms_key.s3[0].key_id, "")
}

output "backup_kms_key_arn" {
  description = "ARN of the backup KMS key"
  value       = try(aws_kms_key.backup[0].arn, "")
}

# ============================================================================
# BACKUP OUTPUTS
# ============================================================================

output "backup_vault_name" {
  description = "Name of the backup vault"
  value       = try(aws_backup_vault.main[0].name, "")
}

output "backup_vault_arn" {
  description = "ARN of the backup vault"
  value       = try(aws_backup_vault.main[0].arn, "")
}

output "backup_plan_id" {
  description = "ID of the backup plan"
  value       = try(aws_backup_plan.main[0].id, "")
}

output "backup_plan_arn" {
  description = "ARN of the backup plan"
  value       = try(aws_backup_plan.main[0].arn, "")
}

output "backup_role_arn" {
  description = "ARN of the backup IAM role"
  value       = try(aws_iam_role.backup[0].arn, "")
}

# ============================================================================
# REPLICATION OUTPUTS (PRODUCTION)
# ============================================================================

output "replica_bucket_names" {
  description = "Names of replica buckets (production only)"
  value       = { for k, v in aws_s3_bucket.replica : k => v.bucket }
}

output "replica_bucket_arns" {
  description = "ARNs of replica buckets (production only)"
  value       = { for k, v in aws_s3_bucket.replica : k => v.arn }
}

output "s3_replication_role_arn" {
  description = "ARN of the S3 replication role"
  value       = try(aws_iam_role.s3_replication[0].arn, "")
}

# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================

output "storage_config_summary" {
  description = "Summary of storage configuration"
  value = {
    dynamodb_tables_count    = length(var.tables_config)
    dynamodb_tables         = keys(var.tables_config)
    s3_buckets_count        = length(var.s3_buckets)
    s3_buckets              = keys(var.s3_buckets)
    encryption_enabled      = anytrue([for table in var.tables_config : table.enable_encryption]) || anytrue([for bucket in var.s3_buckets : bucket.enable_encryption])
    backup_enabled          = var.enable_cross_region_backup
    pitr_enabled            = var.enable_point_in_time_recovery
    replication_enabled     = var.environment == "production"
  }
}

# ============================================================================
# SECURITY INFORMATION
# ============================================================================

output "security_features" {
  description = "Security features enabled"
  value = {
    dynamodb_encryption = anytrue([for table in var.tables_config : table.enable_encryption])
    s3_encryption      = anytrue([for bucket in var.s3_buckets : bucket.enable_encryption])
    s3_public_access_blocked = true
    kms_keys_created   = {
      dynamodb = try(aws_kms_key.dynamodb[0].arn, "") != ""
      s3       = try(aws_kms_key.s3[0].arn, "") != ""
      backup   = try(aws_kms_key.backup[0].arn, "") != ""
    }
    versioning_enabled = {
      for k, v in var.s3_buckets : k => v.enable_versioning
    }
  }
}

# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

output "performance_config" {
  description = "Performance-related configuration"
  value = {
    dynamodb_billing_modes = {
      for k, v in var.tables_config : k => v.billing_mode
    }
    dynamodb_streams_enabled = {
      for k, v in var.tables_config : k => v.enable_streams
    }
    s3_lifecycle_rules = {
      for k, v in var.s3_buckets : k => length(v.lifecycle_rules)
    }
    backup_retention_days = var.backup_retention_days
  }
}

# ============================================================================
# DATA SOURCES
# ============================================================================

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

# ============================================================================
# CONNECTION STRINGS AND ACCESS PATTERNS
# ============================================================================

output "connection_info" {
  description = "Connection information for applications"
  value = {
    dynamodb_region = data.aws_region.current.name
    s3_region       = data.aws_region.current.name
    
    # Environment variables that applications can use
    environment_variables = {
      for k, v in aws_dynamodb_table.tables : 
      "DYNAMODB_TABLE_${upper(k)}" => v.name
    }
  }
}

# ============================================================================
# RESOURCE COUNTS FOR COST TRACKING
# ============================================================================

output "resource_counts" {
  description = "Count of resources for cost tracking"
  value = {
    dynamodb_tables                = length(aws_dynamodb_table.tables)
    s3_buckets                    = length(aws_s3_bucket.buckets)
    kms_keys                      = length(aws_kms_key.dynamodb) + length(aws_kms_key.s3) + length(aws_kms_key.backup)
    backup_vaults                 = length(aws_backup_vault.main)
    replica_buckets               = length(aws_s3_bucket.replica)
    dynamodb_streams_enabled      = length([for k, v in var.tables_config : k if v.enable_streams])
    s3_buckets_with_versioning    = length([for k, v in var.s3_buckets : k if v.enable_versioning])
  }
}