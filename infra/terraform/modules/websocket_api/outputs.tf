output "websocket_api_id" {
  description = "WebSocket API ID"
  value       = aws_apigatewayv2_api.websocket.id
}

output "websocket_api_endpoint" {
  description = "WebSocket API endpoint URL"
  value       = aws_apigatewayv2_api.websocket.api_endpoint
}

output "websocket_stage_name" {
  description = "WebSocket stage name"
  value       = aws_apigatewayv2_stage.websocket.name
}

output "websocket_execution_arn" {
  description = "WebSocket API execution ARN"
  value       = aws_apigatewayv2_api.websocket.execution_arn
}

output "websocket_invoke_url" {
  description = "WebSocket API invoke URL"
  value       = "wss://${aws_apigatewayv2_api.websocket.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_apigatewayv2_stage.websocket.name}"
}

# Data source to get current AWS region
data "aws_region" "current" {}
