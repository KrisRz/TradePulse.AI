# ============================================================================
# Historical Market Context Cache Table
# Auto-deletes data older than 90 days (TTL)
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

  # TTL to auto-delete data older than 90 days
  # App must set 'ttl' field = current_timestamp + 90 days (7776000 seconds)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-market-context-cache"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Purpose     = "Historical market context (90-day data)"
  }
}

output "market_context_cache_table_name" {
  description = "Market context cache table name"
  value       = aws_dynamodb_table.market_context_cache.name
}

output "market_context_cache_table_arn" {
  description = "Market context cache table ARN"
  value       = aws_dynamodb_table.market_context_cache.arn
}
