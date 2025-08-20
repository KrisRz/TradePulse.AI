# TradePulse.AI - Compute Module Outputs
# Professional output definitions for compute resources

# ============================================================================
# LAMBDA FUNCTION OUTPUTS
# ============================================================================

output "lambda_function_names" {
  description = "Names of all Lambda functions"
  value       = { for k, v in aws_lambda_function.functions : k => v.function_name }
}

output "lambda_function_arns" {
  description = "ARNs of all Lambda functions"
  value       = { for k, v in aws_lambda_function.functions : k => v.arn }
}

output "lambda_function_invoke_arns" {
  description = "Invoke ARNs of all Lambda functions"
  value       = { for k, v in aws_lambda_function.functions : k => v.invoke_arn }
}

output "lambda_function_urls" {
  description = "Function URLs for Lambda functions (if configured)"
  value       = { for k, v in aws_lambda_function.functions : k => try(v.function_url, "") }
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_role.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_role.name
}

# ============================================================================
# API GATEWAY OUTPUTS
# ============================================================================

output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = aws_apigatewayv2_api.main.id
}

output "api_gateway_arn" {
  description = "ARN of the API Gateway"
  value       = aws_apigatewayv2_api.main.arn
}

output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = aws_apigatewayv2_stage.main.invoke_url
}

output "api_gateway_domain" {
  description = "Domain name of the API Gateway"
  value       = replace(aws_apigatewayv2_stage.main.invoke_url, "https://", "")
}

output "api_gateway_stage_name" {
  description = "Name of the API Gateway stage"
  value       = aws_apigatewayv2_stage.main.name
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway"
  value       = aws_apigatewayv2_api.main.execution_arn
}

# Custom domain outputs (if configured)
output "custom_api_domain_name" {
  description = "Custom domain name for API (if configured)"
  value       = try(aws_apigatewayv2_domain_name.custom[0].domain_name, "")
}

output "custom_api_domain_target" {
  description = "Target domain name for DNS configuration"
  value       = try(aws_apigatewayv2_domain_name.custom[0].domain_name_configuration[0].target_domain_name, "")
}

# ============================================================================
# EVENTBRIDGE OUTPUTS
# ============================================================================

output "eventbridge_rule_arns" {
  description = "ARNs of EventBridge rules"
  value       = { for k, v in aws_cloudwatch_event_rule.lambda_schedules : k => v.arn }
}

output "eventbridge_rule_names" {
  description = "Names of EventBridge rules"
  value       = { for k, v in aws_cloudwatch_event_rule.lambda_schedules : k => v.name }
}

output "eventbridge_bus_name" {
  description = "Name of the EventBridge bus (default)"
  value       = "default"
}

# ============================================================================
# CLOUDFRONT OUTPUTS
# ============================================================================

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.arn
}

output "cloudfront_domain" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_url" {
  description = "URL of the CloudFront distribution"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "cloudfront_zone_id" {
  description = "Zone ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.hosted_zone_id
}

output "cloudfront_status" {
  description = "Status of the CloudFront distribution"
  value       = aws_cloudfront_distribution.main.status
}

# ============================================================================
# CLOUDWATCH LOG GROUPS
# ============================================================================

output "lambda_log_groups" {
  description = "CloudWatch log groups for Lambda functions"
  value       = { for k, v in aws_cloudwatch_log_group.lambda_logs : k => v.name }
}

output "lambda_log_group_arns" {
  description = "ARNs of Lambda CloudWatch log groups"
  value       = { for k, v in aws_cloudwatch_log_group.lambda_logs : k => v.arn }
}

output "api_gateway_log_group_name" {
  description = "Name of the API Gateway CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway.name
}

output "api_gateway_log_group_arn" {
  description = "ARN of the API Gateway CloudWatch log group"
  value       = aws_cloudwatch_log_group.api_gateway.arn
}

# ============================================================================
# INTEGRATION OUTPUTS
# ============================================================================

output "api_integration_ids" {
  description = "IDs of API Gateway integrations"
  value       = { for k, v in aws_apigatewayv2_integration.lambda : k => v.id }
}

output "api_route_ids" {
  description = "IDs of API Gateway routes"
  value       = { for k, v in aws_apigatewayv2_route.lambda_routes : k => v.id }
}

# ============================================================================
# ENDPOINT INFORMATION
# ============================================================================

output "health_endpoint" {
  description = "Health check endpoint URL"
  value       = "${aws_apigatewayv2_stage.main.invoke_url}/health"
}

output "api_endpoints" {
  description = "Key API endpoint URLs"
  value = {
    base_url    = aws_apigatewayv2_stage.main.invoke_url
    health      = "${aws_apigatewayv2_stage.main.invoke_url}/health"
    ai_signals  = "${aws_apigatewayv2_stage.main.invoke_url}/ai"
    docs        = "${aws_apigatewayv2_stage.main.invoke_url}/docs"
    metrics     = "${aws_apigatewayv2_stage.main.invoke_url}/metrics"
  }
}

output "webhook_endpoints" {
  description = "Webhook endpoint URLs for external integrations"
  value = {
    binance_webhook = "${aws_apigatewayv2_stage.main.invoke_url}/webhook/binance"
    trading_signals = "${aws_apigatewayv2_stage.main.invoke_url}/webhook/signals"
    system_alerts   = "${aws_apigatewayv2_stage.main.invoke_url}/webhook/alerts"
  }
}

# ============================================================================
# RESOURCE SUMMARY
# ============================================================================

output "resource_summary" {
  description = "Summary of created compute resources"
  value = {
    lambda_functions_count    = length(var.lambda_functions)
    lambda_functions         = keys(var.lambda_functions)
    api_gateway_routes_count = length(aws_apigatewayv2_route.lambda_routes)
    eventbridge_rules_count  = length(var.eventbridge_rules)
    cloudfront_enabled       = true
    custom_domain_configured = var.api_gateway_config.custom_domain != null
    xray_tracing_enabled     = var.enable_xray_tracing
  }
}

# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

output "performance_config" {
  description = "Performance-related configuration"
  value = {
    api_throttle_burst  = var.api_gateway_config.throttle_burst
    api_throttle_rate   = var.api_gateway_config.throttle_rate
    lambda_concurrency  = var.max_lambda_concurrency
    cloudfront_price_class = var.cloudfront_config.price_class
    log_retention_days  = var.log_retention_days
  }
}