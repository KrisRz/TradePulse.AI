# TradePulse.AI - Storage Module
# DynamoDB Tables, S3 Buckets, Backup Configuration
# Enterprise-grade data storage and management

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}-${var.deployment_id}"
  
  common_tags = merge(var.tags, {
    Module = "storage"
    Service = "data-storage"
  })
}

# ============================================================================
# DYNAMODB TABLES
# ============================================================================

resource "aws_dynamodb_table" "tables" {
  for_each = var.tables_config
  
  name = (
    contains(keys(var.explicit_table_names), each.key)
    ? var.explicit_table_names[each.key]
    : "${var.project_name}-${each.key}-${var.environment}"
  )
  billing_mode   = each.value.billing_mode
  hash_key       = each.value.hash_key
  range_key      = each.value.range_key
  
  # Provisioned capacity (only if billing mode is PROVISIONED)
  dynamic "attribute" {
    for_each = compact([each.value.hash_key, each.value.range_key])
    content {
      name = attribute.value
      type = "S"  # All keys are strings for simplicity
    }
  }
  
  # Additional attributes for GSI
  dynamic "attribute" {
    for_each = lookup(each.value, "gsi_attributes", [])
    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }
  
  # Global Secondary Indexes
  dynamic "global_secondary_index" {
    for_each = lookup(each.value, "global_secondary_indexes", [])
    content {
      name            = global_secondary_index.value.name
      hash_key        = global_secondary_index.value.hash_key
      range_key       = global_secondary_index.value.range_key
      projection_type = global_secondary_index.value.projection_type
      
      dynamic "non_key_attributes" {
        for_each = lookup(global_secondary_index.value, "non_key_attributes", [])
        content {
          non_key_attributes = non_key_attributes.value
        }
      }
    }
  }
  
  # Local Secondary Indexes
  dynamic "local_secondary_index" {
    for_each = lookup(each.value, "local_secondary_indexes", [])
    content {
      name            = local_secondary_index.value.name
      range_key       = local_secondary_index.value.range_key
      projection_type = local_secondary_index.value.projection_type
    }
  }
  
  # TTL configuration
  dynamic "ttl" {
    for_each = each.value.ttl_attribute != null ? [1] : []
    content {
      attribute_name = each.value.ttl_attribute
      enabled        = true
    }
  }
  
  # DynamoDB Streams
  dynamic "stream_specification" {
    for_each = each.value.enable_streams ? [1] : []
    content {
      enabled   = true
      view_type = "NEW_AND_OLD_IMAGES"
    }
  }
  
  # Server-side encryption
  server_side_encryption {
    enabled     = each.value.enable_encryption
    kms_key_id  = each.value.enable_encryption ? aws_kms_key.dynamodb[0].arn : null
  }
  
  # Point-in-time recovery
  point_in_time_recovery {
    enabled = each.value.enable_pitr
  }
  
  # Deletion protection for production
  deletion_protection_enabled = var.environment == "production"
  
  tags = merge(local.common_tags, {
    TableType = each.key
    DataType = "trading-data"
  })
  
  lifecycle {
    prevent_destroy = true
  }
}

# KMS Key for DynamoDB encryption
resource "aws_kms_key" "dynamodb" {
  count = anytrue([for table in var.tables_config : table.enable_encryption]) ? 1 : 0
  
  description             = "KMS key for DynamoDB encryption - ${local.name_prefix}"
  deletion_window_in_days = var.environment == "production" ? 30 : 7
  
  tags = merge(local.common_tags, {
    Service = "dynamodb-encryption"
  })
}

# KMS Key alias
resource "aws_kms_alias" "dynamodb" {
  count = anytrue([for table in var.tables_config : table.enable_encryption]) ? 1 : 0
  
  name          = "alias/${local.name_prefix}-dynamodb"
  target_key_id = aws_kms_key.dynamodb[0].key_id
}

# ============================================================================
# S3 BUCKETS
# ============================================================================

resource "aws_s3_bucket" "buckets" {
  for_each = var.s3_buckets
  
  bucket = (
    contains(keys(var.explicit_bucket_names), each.key)
    ? var.explicit_bucket_names[each.key]
    : "${var.project_name}-${each.key}-${var.environment}-${random_id.bucket_suffix[each.key].hex}"
  )
  
  tags = merge(local.common_tags, {
    BucketType = each.key
    Purpose    = each.value.purpose
  })
  
  lifecycle {
    prevent_destroy = true
  }
}

# Random suffix for bucket names to ensure uniqueness
resource "random_id" "bucket_suffix" {
  for_each = var.s3_buckets
  
  byte_length = 4
  keepers = {
    bucket_type = each.key
    project     = var.project_name
    environment = var.environment
  }
}

# S3 Bucket versioning
resource "aws_s3_bucket_versioning" "buckets" {
  for_each = var.s3_buckets
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  versioning_configuration {
    status = each.value.enable_versioning ? "Enabled" : "Suspended"
  }
}

# S3 Bucket server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "buckets" {
  for_each = var.s3_buckets
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = each.value.enable_encryption ? "aws:kms" : "AES256"
      kms_master_key_id = each.value.enable_encryption ? aws_kms_key.s3[0].arn : null
    }
    bucket_key_enabled = each.value.enable_encryption
  }
}

# KMS Key for S3 encryption
resource "aws_kms_key" "s3" {
  count = anytrue([for bucket in var.s3_buckets : bucket.enable_encryption]) ? 1 : 0
  
  description             = "KMS key for S3 encryption - ${local.name_prefix}"
  deletion_window_in_days = var.environment == "production" ? 30 : 7
  
  tags = merge(local.common_tags, {
    Service = "s3-encryption"
  })
}

# KMS Key alias for S3
resource "aws_kms_alias" "s3" {
  count = anytrue([for bucket in var.s3_buckets : bucket.enable_encryption]) ? 1 : 0
  
  name          = "alias/${local.name_prefix}-s3"
  target_key_id = aws_kms_key.s3[0].key_id
}

# S3 Bucket public access block
resource "aws_s3_bucket_public_access_block" "buckets" {
  for_each = var.s3_buckets
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket CORS configuration (for frontend bucket)
resource "aws_s3_bucket_cors_configuration" "frontend" {
  for_each = {
    for k, v in var.s3_buckets : k => v
    if v.enable_cors
  }
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# S3 Bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "buckets" {
  for_each = {
    for k, v in var.s3_buckets : k => v
    if length(v.lifecycle_rules) > 0
  }
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  dynamic "rule" {
    for_each = each.value.lifecycle_rules
    content {
      id     = rule.value.id
      status = rule.value.status
      
      dynamic "transition" {
        for_each = rule.value.expiration_days == null ? [rule.value] : []
        content {
          days          = transition.value.transition_days
          storage_class = transition.value.transition_storage_class
        }
      }
      
      dynamic "expiration" {
        for_each = rule.value.expiration_days != null ? [rule.value] : []
        content {
          days = expiration.value.expiration_days
        }
      }
      
      # Handle non-current versions
      noncurrent_version_expiration {
        noncurrent_days = 90
      }
    }
  }
}

# S3 Bucket website configuration (for frontend)
resource "aws_s3_bucket_website_configuration" "frontend" {
  for_each = {
    for k, v in var.s3_buckets : k => v
    if v.purpose == "static-website"
  }
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  index_document {
    suffix = "index.html"
  }
  
  error_document {
    key = "error.html"
  }
}

# S3 Bucket policy for CloudFront access (frontend bucket)
resource "aws_s3_bucket_policy" "frontend_cloudfront" {
  for_each = {
    for k, v in var.s3_buckets : k => v
    if v.purpose == "static-website"
  }
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.buckets[each.key].arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = var.cloudfront_distribution_arn
          }
        }
      }
    ]
  })
}

# ============================================================================
# BACKUP CONFIGURATION
# ============================================================================

# AWS Backup Vault
resource "aws_backup_vault" "main" {
  count = var.enable_cross_region_backup ? 1 : 0
  
  name        = "${local.name_prefix}-backup-vault"
  kms_key_arn = aws_kms_key.backup[0].arn
  
  tags = local.common_tags
}

# KMS Key for backups
resource "aws_kms_key" "backup" {
  count = var.enable_cross_region_backup ? 1 : 0
  
  description             = "KMS key for AWS Backup - ${local.name_prefix}"
  deletion_window_in_days = var.environment == "production" ? 30 : 7
  
  tags = merge(local.common_tags, {
    Service = "backup-encryption"
  })
}

# KMS Key alias for backup
resource "aws_kms_alias" "backup" {
  count = var.enable_cross_region_backup ? 1 : 0
  
  name          = "alias/${local.name_prefix}-backup"
  target_key_id = aws_kms_key.backup[0].key_id
}

# IAM role for AWS Backup
resource "aws_iam_role" "backup" {
  count = var.enable_cross_region_backup ? 1 : 0
  
  name = "${local.name_prefix}-backup-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach backup service role policy
resource "aws_iam_role_policy_attachment" "backup_service_role" {
  count = var.enable_cross_region_backup ? 1 : 0
  
  role       = aws_iam_role.backup[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

# Backup plan
resource "aws_backup_plan" "main" {
  count = var.enable_cross_region_backup ? 1 : 0
  
  name = "${local.name_prefix}-backup-plan"
  
  rule {
    rule_name         = "daily_backup"
    target_vault_name = aws_backup_vault.main[0].name
    schedule          = "cron(0 2 ? * * *)"  # Daily at 2 AM UTC
    
    lifecycle {
      cold_storage_after = 30
      delete_after       = var.backup_retention_days
    }
    
    recovery_point_tags = local.common_tags
  }
  
  # Weekly backup rule
  rule {
    rule_name         = "weekly_backup"
    target_vault_name = aws_backup_vault.main[0].name
    schedule          = "cron(0 3 ? * 1 *)"  # Weekly on Monday at 3 AM UTC
    
    lifecycle {
      cold_storage_after = 30
      delete_after       = var.backup_retention_days * 2
    }
    
    recovery_point_tags = merge(local.common_tags, {
      BackupType = "weekly"
    })
  }
  
  tags = local.common_tags
}

# Backup selection for DynamoDB tables
resource "aws_backup_selection" "dynamodb" {
  count = var.enable_cross_region_backup ? 1 : 0
  
  iam_role_arn = aws_iam_role.backup[0].arn
  name         = "${local.name_prefix}-dynamodb-backup"
  plan_id      = aws_backup_plan.main[0].id
  
  resources = [
    for table in aws_dynamodb_table.tables : table.arn
  ]
  
  condition {
    string_equals {
      key   = "aws:ResourceTag/Environment"
      value = var.environment
    }
  }
}

# ============================================================================
# REPLICATION (for production)
# ============================================================================

# S3 bucket replication configuration (for critical buckets in production)
resource "aws_s3_bucket_replication_configuration" "main" {
  for_each = var.environment == "production" ? {
    for k, v in var.s3_buckets : k => v
    if contains(["data", "models", "backups"], k)
  } : {}
  
  depends_on = [aws_s3_bucket_versioning.buckets]
  
  role   = aws_iam_role.s3_replication[0].arn
  bucket = aws_s3_bucket.buckets[each.key].id
  
  rule {
    id     = "replicate-${each.key}"
    status = "Enabled"
    
    destination {
      bucket        = aws_s3_bucket.replica[each.key].arn
      storage_class = "STANDARD_IA"
      
      encryption_configuration {
        replica_kms_key_id = aws_kms_key.s3[0].arn
      }
    }
  }
}

# Replica buckets in different region (production only)
resource "aws_s3_bucket" "replica" {
  for_each = var.environment == "production" ? {
    for k, v in var.s3_buckets : k => v
    if contains(["data", "models", "backups"], k)
  } : {}
  
  provider = aws.replica
  
  bucket = "${local.name_prefix}-${each.key}-replica-${random_id.replica_suffix[each.key].hex}"
  
  tags = merge(local.common_tags, {
    BucketType = "${each.key}-replica"
    Purpose    = "disaster-recovery"
  })
}

# Random suffix for replica buckets
resource "random_id" "replica_suffix" {
  for_each = var.environment == "production" ? {
    for k, v in var.s3_buckets : k => v
    if contains(["data", "models", "backups"], k)
  } : {}
  
  byte_length = 4
}

# IAM role for S3 replication
resource "aws_iam_role" "s3_replication" {
  count = var.environment == "production" ? 1 : 0
  
  name = "${local.name_prefix}-s3-replication-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# IAM policy for S3 replication
resource "aws_iam_role_policy" "s3_replication" {
  count = var.environment == "production" ? 1 : 0
  
  name = "${local.name_prefix}-s3-replication-policy"
  role = aws_iam_role.s3_replication[0].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Resource = [
          for bucket in aws_s3_bucket.buckets : "${bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          for bucket in aws_s3_bucket.buckets : bucket.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Resource = [
          for bucket in aws_s3_bucket.replica : "${bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [
          aws_kms_key.s3[0].arn
        ]
      }
    ]
  })
}