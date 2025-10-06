# ============================================================================
# Live Candles Table (Real-time Binance data with TTL)
# ============================================================================

resource "aws_dynamodb_table" "live_candles" {
  name         = "tradepulse-live_candles-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "pk"
  range_key = "ts"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "ts"
    type = "N"
  }

  # TTL to auto-delete candles older than 90 days
  # App sets: ttl = current_timestamp + 7776000 (90 days in seconds)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-live-candles"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Real-time 1m candles from Binance (auto-delete > 90 days)"
  }
}

output "live_candles_table_name" {
  description = "Live candles table name"
  value       = aws_dynamodb_table.live_candles.name
}

output "live_candles_table_arn" {
  description = "Live candles table ARN"
  value       = aws_dynamodb_table.live_candles.arn
}
