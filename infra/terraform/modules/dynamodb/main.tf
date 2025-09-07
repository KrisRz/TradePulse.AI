# Main trading data table (single-table design for TradePulse.AI)
resource "aws_dynamodb_table" "main" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST" # Cost-effective for variable trading workload
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "gsi1pk"
    type = "S"
  }

  attribute {
    name = "gsi1sk"
    type = "S"
  }

  attribute {
    name = "gsi2pk"
    type = "S"
  }

  attribute {
    name = "gsi2sk"
    type = "S"
  }

  # GSI for trading signals by strategy and time
  global_secondary_index {
    name            = "GSI1"
    hash_key        = "gsi1pk"
    range_key       = "gsi1sk"
    projection_type = "ALL"
  }

  # GSI for user data queries
  global_secondary_index {
    name            = "GSI2"
    hash_key        = "gsi2pk"
    range_key       = "gsi2sk"
    projection_type = "ALL"
  }

  # TTL for temporary data (logs, sessions)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery for production
  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  # Server-side encryption
  server_side_encryption {
    enabled = true
  }

  # DynamoDB Streams for real-time processing
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = var.tags
}

# WebSocket connections table
resource "aws_dynamodb_table" "connections" {
  name         = "${var.app_name}-${var.env}-connections"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "connection_id"

  attribute {
    name = "connection_id"
    type = "S"
  }

  # TTL for automatic cleanup of stale connections (1 hour)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = var.tags
}

# Market data cache table (high-frequency reads/writes)
resource "aws_dynamodb_table" "market_data_cache" {
  name         = "${var.app_name}-${var.env}-market-cache"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "symbol"
  range_key    = "timestamp"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  # TTL for automatic cleanup (keep only recent data - 24 hours)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # DynamoDB Streams for real-time distribution
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = var.tags
}
