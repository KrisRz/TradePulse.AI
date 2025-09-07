# Lambda function outputs
output "lambda_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.this.function_name
}

output "lambda_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.this.arn
}

output "lambda_invoke_arn" {
  description = "Lambda function invoke ARN"
  value       = aws_lambda_function.this.invoke_arn
}

# API Gateway outputs
output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "api_domain_name" {
  description = "API Gateway domain name (without https://)"
  value       = replace(aws_apigatewayv2_api.http.api_endpoint, "https://", "")
}

output "api_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.http.id
}

output "api_execution_arn" {
  description = "API Gateway execution ARN"
  value       = aws_apigatewayv2_api.http.execution_arn
}
