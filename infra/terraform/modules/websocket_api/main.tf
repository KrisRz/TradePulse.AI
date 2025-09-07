# WebSocket API Gateway for real-time Bitcoin price streaming
resource "aws_apigatewayv2_api" "websocket" {
  name                       = "${var.app_name}-${var.env}-websocket"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
  description                = "Real-time Bitcoin price streaming for TradePulse.AI"

  tags = var.tags
}

# CloudWatch Log Group for WebSocket API
resource "aws_cloudwatch_log_group" "websocket_api" {
  name              = "/aws/apigateway/${var.app_name}-${var.env}-websocket"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# Connection management routes
resource "aws_apigatewayv2_route" "connect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.connect.id}"

  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.websocket.id
}

resource "aws_apigatewayv2_route" "disconnect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.disconnect.id}"
}

resource "aws_apigatewayv2_route" "subscribe" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "subscribe"
  target    = "integrations/${aws_apigatewayv2_integration.subscribe.id}"
}

resource "aws_apigatewayv2_route" "unsubscribe" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "unsubscribe"
  target    = "integrations/${aws_apigatewayv2_integration.unsubscribe.id}"
}

# WebSocket authorizer for JWT validation
resource "aws_apigatewayv2_authorizer" "websocket" {
  api_id                           = aws_apigatewayv2_api.websocket.id
  authorizer_type                  = "REQUEST"
  authorizer_uri                   = var.websocket_authorizer_lambda_arn
  name                             = "${var.app_name}-${var.env}-ws-authorizer"
  identity_sources                 = ["route.request.querystring.token"]
  authorizer_result_ttl_in_seconds = 300
}

# Lambda integrations
resource "aws_apigatewayv2_integration" "connect" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = var.connection_handler_lambda_arn

  integration_method = "POST"
}

resource "aws_apigatewayv2_integration" "disconnect" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = var.connection_handler_lambda_arn

  integration_method = "POST"
}

resource "aws_apigatewayv2_integration" "subscribe" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = var.connection_handler_lambda_arn

  integration_method = "POST"
}

resource "aws_apigatewayv2_integration" "unsubscribe" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = var.connection_handler_lambda_arn

  integration_method = "POST"
}

# Deployment
resource "aws_apigatewayv2_deployment" "websocket" {
  api_id = aws_apigatewayv2_api.websocket.id

  depends_on = [
    aws_apigatewayv2_route.connect,
    aws_apigatewayv2_route.disconnect,
    aws_apigatewayv2_route.subscribe,
    aws_apigatewayv2_route.unsubscribe
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# Stage
resource "aws_apigatewayv2_stage" "websocket" {
  api_id        = aws_apigatewayv2_api.websocket.id
  deployment_id = aws_apigatewayv2_deployment.websocket.id
  name          = var.env

  # Throttling settings
  default_route_settings {
    throttling_rate_limit  = var.throttling_rate_limit
    throttling_burst_limit = var.throttling_burst_limit
  }

  # Access logging
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.websocket_api.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      error          = "$context.error.message"
      responseLength = "$context.responseLength"
    })
  }

  tags = var.tags
}

# Lambda permissions for API Gateway to invoke functions
resource "aws_lambda_permission" "websocket_authorizer" {
  statement_id  = "AllowWebSocketAuthorizerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.websocket_authorizer_lambda_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/*"
}

resource "aws_lambda_permission" "connection_handler" {
  statement_id  = "AllowWebSocketConnectionHandlerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.connection_handler_lambda_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/*"
}
