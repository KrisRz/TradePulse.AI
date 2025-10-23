# ============================================================================
# Historical Market Context Cache Table (Day Trading Optimized)
# - Uses last 14 days of data for relevant intraday patterns
# - Refreshes every 4 hours for fresh pattern calculations
# - Auto-deletes data older than 14 days (TTL)
# ============================================================================

resource "aws_dynamodb_table" "market_context_cache" {
  name         = "market_context_cache"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "symbol"
  range_key = "period"

  attribute {
    name = "symbol"
    type = "S"
  }

  attribute {
    name = "period"
    type = "S"
  }

  # TTL to auto-delete data older than 14 days (day trading mode)
  # App sets 'ttl' field = current_timestamp + 14 days (1209600 seconds)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-market-context-cache"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Historical market context 14-day data day trading optimized"
  }
}

output "market_context_cache_table_name" {
  description = "Market context cache table name (day trading: 14D/4h refresh)"
  value       = aws_dynamodb_table.market_context_cache.name
}

output "market_context_cache_table_arn" {
  description = "Market context cache table ARN"
  value       = aws_dynamodb_table.market_context_cache.arn
}
