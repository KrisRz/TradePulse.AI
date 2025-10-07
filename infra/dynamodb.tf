# DynamoDB tables for TradePulse.AI
# Using on-demand billing mode for production-ready scaling

resource "aws_dynamodb_table" "signals" {
  name             = "${var.project_name}_signals"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "pk"
  range_key        = "sk"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  global_secondary_index {
    name            = "symbol-timestamp-index"
    hash_key        = "symbol"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-signals"
  }
}

resource "aws_dynamodb_table" "portfolio" {
  name         = "${var.project_name}_portfolio"
  billing_mode = "PAY_PER_REQUEST"
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
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user-id-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-portfolio"
  }
}

resource "aws_dynamodb_table" "positions" {
  name         = "${var.project_name}_positions"
  billing_mode = "PAY_PER_REQUEST"
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
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "symbol-status-index"
    hash_key        = "symbol"
    range_key       = "status"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-positions"
  }
}

resource "aws_dynamodb_table" "analytics" {
  name         = "${var.project_name}_analytics"
  billing_mode = "PAY_PER_REQUEST"
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
    name = "timestamp"
    type = "N"
  }

  global_secondary_index {
    name            = "timestamp-index"
    hash_key        = "pk"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-analytics"
  }
}

resource "aws_dynamodb_table" "brain_state" {
  name         = "${var.project_name}_brain_state"
  billing_mode = "PAY_PER_REQUEST"
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

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-brain-state"
  }
}

# Removed duplicate market_data and runtime tables - using versions from dynamodb-app-tables.tf

# Optional: DynamoDB VPC Endpoint for cost optimization
resource "aws_vpc_endpoint" "dynamodb" {
  count = var.enable_vpc ? 1 : 0

  vpc_id            = aws_vpc.main[0].id
  service_name      = "com.amazonaws.${var.region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_vpc.main[0].main_route_table_id]

  tags = {
    Name = "${var.project_name}-dynamodb-endpoint"
  }
}
