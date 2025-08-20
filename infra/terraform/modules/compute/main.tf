# TradePulse.AI - Compute Module
# Lambda Functions, API Gateway, EventBridge, CloudFront
# Enterprise-grade serverless computing infrastructure

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}-${var.deployment_id}"
  
  common_tags = merge(var.tags, {
    Module = "compute"
    Service = "serverless-compute"
  })
}

# ============================================================================
# IAM ROLES FOR LAMBDA FUNCTIONS
# ============================================================================

# Main Lambda execution role
resource "aws_iam_role" "lambda_role" {
  name = "${local.name_prefix}-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# Enhanced Lambda policy with all necessary permissions
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${local.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Basic Lambda execution
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream", 
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      # VPC access (if enabled)
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AttachNetworkInterface",
          "ec2:DetachNetworkInterface"
        ]
        Resource = "*"
      },
      # DynamoDB full access for trading data
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:DescribeTable",
          "dynamodb:DescribeStream",
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:ListStreams"
        ]
        Resource = var.dynamodb_table_arns
      },
      # S3 access for data and models
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = concat(var.s3_bucket_arns, [for arn in var.s3_bucket_arns : "${arn}/*"])
      },
      # Secrets Manager access
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = var.secrets_manager_arns
      },
      # EventBridge permissions for scheduling
      {
        Effect = "Allow"
        Action = [
          "events:PutEvents"
        ]
        Resource = "*"
      },
      # X-Ray tracing
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      },
      # SNS for notifications
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = "*"
      },
      # Lambda invoke permissions for inter-function calls
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:*:*:function:${local.name_prefix}-*"
      }
    ]
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach VPC execution policy if VPC is enabled
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count = var.vpc_id != null ? 1 : 0
  
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# ============================================================================
# LAMBDA FUNCTIONS
# ============================================================================

resource "aws_lambda_function" "functions" {
  for_each = var.lambda_functions
  
  filename      = each.value.filename
  function_name = (
    contains(keys(var.explicit_function_names), each.key)
    ? var.explicit_function_names[each.key]
    : "${local.name_prefix}-${each.key}"
  )
  role         = aws_iam_role.lambda_role.arn
  handler      = each.value.handler
  runtime      = each.value.runtime
  timeout      = each.value.timeout
  memory_size  = each.value.memory_size
  
  # Source code hash for updates
  source_code_hash = filebase64sha256(each.value.filename)
  
  # Environment variables
  environment {
    variables = merge(each.value.environment_vars, {
      FUNCTION_NAME = "${local.name_prefix}-${each.key}"
      AWS_LAMBDA_FUNCTION_NAME = "${local.name_prefix}-${each.key}"
    })
  }
  
  # VPC configuration if provided
  dynamic "vpc_config" {
    for_each = each.value.vpc_config != null ? [each.value.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }
  
  # X-Ray tracing
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }
  
  # Reserved concurrency to prevent cost spirals
  reserved_concurrent_executions = var.max_lambda_concurrency
  
  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_cloudwatch_log_group.lambda_logs
  ]
  
  tags = merge(local.common_tags, {
    FunctionType = each.key
  })
}

# CloudWatch Log Groups for Lambda functions
resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = var.lambda_functions
  
  name              = "/aws/lambda/${local.name_prefix}-${each.key}"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# ============================================================================
# API GATEWAY HTTP API
# ============================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = var.api_gateway_config.name
  description   = var.api_gateway_config.description
  protocol_type = var.api_gateway_config.protocol_type
  
  # CORS configuration
  dynamic "cors_configuration" {
    for_each = var.api_gateway_config.cors_enabled ? [1] : []
    content {
      allow_credentials = false
      allow_headers     = ["content-type", "authorization", "x-amz-date", "x-api-key", "x-amz-security-token"]
      allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
      allow_origins     = ["*"]
      expose_headers    = []
      max_age          = 86400
    }
  }
  
  tags = local.common_tags
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "production"
  auto_deploy = true
  
  # Throttling configuration
  throttle_config {
    burst_limit = var.api_gateway_config.throttle_burst
    rate_limit  = var.api_gateway_config.throttle_rate
  }
  
  # Access logging
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip            = "$context.identity.sourceIp"
      requestTime   = "$context.requestTime"
      httpMethod    = "$context.httpMethod"
      routeKey      = "$context.routeKey"
      status        = "$context.status"
      protocol      = "$context.protocol"
      responseLength = "$context.responseLength"
      error         = "$context.error.message"
      integrationError = "$context.integration.error"
    })
  }
  
  tags = local.common_tags
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigatewayv2/${aws_apigatewayv2_api.main.name}"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# Lambda integrations for API Gateway
resource "aws_apigatewayv2_integration" "lambda" {
  for_each = {
    for k, v in var.lambda_functions : k => v
    if contains(["backend_api", "ai_signals"], k) # Only for API functions
  }
  
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.functions[each.key].invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = each.value.timeout * 1000
}

# API Gateway routes
resource "aws_apigatewayv2_route" "lambda_routes" {
  for_each = {
    "backend_api" = {
      route_key = "ANY /{proxy+}"
      target    = "backend_api"
    }
    "ai_signals" = {
      route_key = "POST /ai/{proxy+}"
      target    = "ai_signals"
    }
    "health" = {
      route_key = "GET /health"
      target    = "backend_api"
    }
  }
  
  api_id    = aws_apigatewayv2_api.main.id
  route_key = each.value.route_key
  target    = "integrations/${aws_apigatewayv2_integration.lambda[each.value.target].id}"
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  for_each = {
    for k, v in var.lambda_functions : k => v
    if contains(["backend_api", "ai_signals"], k)
  }
  
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.functions[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Custom domain for API Gateway (if provided)
resource "aws_apigatewayv2_domain_name" "custom" {
  count = var.api_gateway_config.custom_domain != null ? 1 : 0
  
  domain_name = "api.${var.api_gateway_config.custom_domain}"
  
  domain_name_configuration {
    certificate_arn = var.api_gateway_config.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
  
  tags = local.common_tags
}

# API mapping for custom domain
resource "aws_apigatewayv2_api_mapping" "custom" {
  count = var.api_gateway_config.custom_domain != null ? 1 : 0
  
  api_id      = aws_apigatewayv2_api.main.id
  domain_name = aws_apigatewayv2_domain_name.custom[0].id
  stage       = aws_apigatewayv2_stage.main.id
}

# ============================================================================
# EVENTBRIDGE RULES FOR SCHEDULING
# ============================================================================

resource "aws_cloudwatch_event_rule" "lambda_schedules" {
  for_each = var.eventbridge_rules
  
  name                = "${local.name_prefix}-${each.key}"
  description         = each.value.description
  schedule_expression = each.value.schedule_expression
  
  tags = local.common_tags
}

# EventBridge targets (Lambda functions)
resource "aws_cloudwatch_event_target" "lambda_targets" {
  for_each = var.eventbridge_rules
  
  rule      = aws_cloudwatch_event_rule.lambda_schedules[each.key].name
  target_id = "${each.key}-target"
  arn       = aws_lambda_function.functions[each.value.target_function].arn
  input     = each.value.input
}

# Lambda permissions for EventBridge
resource "aws_lambda_permission" "eventbridge" {
  for_each = var.eventbridge_rules
  
  statement_id  = "AllowExecutionFromEventBridge-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.functions[each.value.target_function].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_schedules[each.key].arn
}

# ============================================================================
# CLOUDFRONT DISTRIBUTION
# ============================================================================

# Origin Access Control for S3
resource "aws_cloudfront_origin_access_control" "s3_oac" {
  name                              = "${local.name_prefix}-s3-oac"
  description                      = "OAC for TradePulse.AI S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                 = "always"
  signing_protocol                 = "sigv4"
}

# CloudFront distribution
resource "aws_cloudfront_distribution" "main" {
  comment             = "TradePulse.AI ${var.environment} distribution"
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = var.cloudfront_config.price_class
  
  # S3 origin for static assets
  origin {
    domain_name              = var.cloudfront_config.frontend_bucket_domain
    origin_id                = "S3-${var.cloudfront_config.frontend_bucket_id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.s3_oac.id
  }
  
  # API Gateway origin
  origin {
    domain_name = replace(var.cloudfront_config.api_domain, "https://", "")
    origin_id   = "APIGateway"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }
  
  # Default behavior (S3)
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${var.cloudfront_config.frontend_bucket_id}"
    compress         = true
    
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }
  
  # API behavior
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "APIGateway"
    compress         = true
    
    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type"]
      cookies {
        forward = "all"
      }
    }
    
    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }
  
  # Geographic restrictions
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  
  # SSL Certificate
  viewer_certificate {
    cloudfront_default_certificate = var.cloudfront_config.custom_domain == null
    
    dynamic "viewer_certificate" {
      for_each = var.cloudfront_config.custom_domain != null ? [1] : []
      content {
        acm_certificate_arn      = var.cloudfront_config.certificate_arn
        ssl_support_method       = "sni-only"
        minimum_protocol_version = "TLSv1.2_2021"
      }
    }
  }
  
  # Custom domain aliases
  dynamic "aliases" {
    for_each = var.cloudfront_config.custom_domain != null ? [var.cloudfront_config.custom_domain] : []
    content {
      aliases = [aliases.value]
    }
  }
  
  # Error pages
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }
  
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }
  
  tags = local.common_tags
}