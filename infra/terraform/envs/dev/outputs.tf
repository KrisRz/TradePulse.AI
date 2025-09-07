# API Gateway outputs
output "api_url" {
  description = "API Gateway endpoint URL"
  value       = module.api.api_endpoint
}

output "api_id" {
  description = "API Gateway ID"
  value       = module.api.api_id
}

# WebSocket API outputs
output "websocket_url" {
  description = "WebSocket API endpoint URL"
  value       = module.websocket_api.websocket_invoke_url
}

output "websocket_api_id" {
  description = "WebSocket API ID"
  value       = module.websocket_api.websocket_api_id
}

# Frontend outputs
output "bucket_name" {
  description = "S3 bucket name for frontend"
  value       = module.frontend.bucket_name
}

output "cloudfront_url" {
  description = "CloudFront distribution domain name"
  value       = module.frontend.cf_domain_name
}

output "cloudfront_id" {
  description = "CloudFront distribution ID"
  value       = module.frontend.cf_id
}

output "app_domain" {
  description = "Application domain name"
  value       = module.dns.app_domain
}

# Database outputs
output "dynamodb_table_name" {
  description = "Main DynamoDB table name"
  value       = module.database.table_name
}

output "connections_table_name" {
  description = "WebSocket connections table name"
  value       = module.database.connections_table_name
}

output "market_cache_table_name" {
  description = "Market data cache table name"
  value       = module.database.market_cache_table_name
}

# S3 bucket outputs
output "models_bucket" {
  description = "S3 bucket for AI models"
  value       = aws_s3_bucket.models.bucket
}

output "layers_bucket" {
  description = "S3 bucket for Lambda layers"
  value       = aws_s3_bucket.lambda_layers.bucket
}

# Step Functions outputs
output "ai_pipeline_arn" {
  description = "AI pipeline Step Function ARN"
  value       = module.step_functions.ai_pipeline_arn
}

output "model_retraining_arn" {
  description = "Model retraining Step Function ARN"
  value       = module.step_functions.model_retraining_arn
}

output "emergency_halt_arn" {
  description = "Emergency halt Step Function ARN"
  value       = module.step_functions.emergency_halt_arn
}

# EventBridge outputs
output "trading_event_bus_name" {
  description = "Trading events EventBridge bus name"
  value       = module.eventbridge.trading_bus_name
}

# Monitoring outputs
output "dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.monitoring.dashboard_url
}

# Lambda layers outputs
output "lambda_layer_arns" {
  description = "Map of all Lambda layer ARNs"
  value       = module.lambda_layers.all_layer_arns
  sensitive   = false
}
