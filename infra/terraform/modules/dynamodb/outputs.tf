# Main table outputs
output "table_name" {
  description = "Main DynamoDB table name"
  value       = aws_dynamodb_table.main.name
}

output "table_arn" {
  description = "Main DynamoDB table ARN"
  value       = aws_dynamodb_table.main.arn
}

output "table_stream_arn" {
  description = "Main DynamoDB table stream ARN"
  value       = aws_dynamodb_table.main.stream_arn
}

# Connections table outputs
output "connections_table_name" {
  description = "WebSocket connections table name"
  value       = aws_dynamodb_table.connections.name
}

output "connections_table_arn" {
  description = "WebSocket connections table ARN"
  value       = aws_dynamodb_table.connections.arn
}

# Market data cache table outputs
output "market_cache_table_name" {
  description = "Market data cache table name"
  value       = aws_dynamodb_table.market_data_cache.name
}

output "market_cache_table_arn" {
  description = "Market data cache table ARN"
  value       = aws_dynamodb_table.market_data_cache.arn
}

output "market_cache_stream_arn" {
  description = "Market data cache table stream ARN"
  value       = aws_dynamodb_table.market_data_cache.stream_arn
}
