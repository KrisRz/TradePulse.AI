# ============================================================================
# EventBridge Schedule for Historical Context Refresh
# Runs daily at 00:00 UTC to fetch fresh 90-day data from Binance
# ============================================================================

# TODO: Uncomment when Lambda function is deployed
# This requires Lambda function to be created first

# # EventBridge rule - daily at midnight UTC
# resource "aws_cloudwatch_event_rule" "historical_context_refresh" {
#   name                = "${var.project_name}-historical-context-refresh"
#   description         = "Daily refresh of historical market context (90-day data from Binance)"
#   schedule_expression = "cron(0 0 * * ? *)"  # Daily at 00:00 UTC
#   
#   tags = {
#     Name        = "${var.project_name}-historical-refresh-rule"
#     Project     = var.project_name
#     Environment = var.environment
#     ManagedBy   = "Terraform"
#   }
# }

# # EventBridge target - Lambda function
# resource "aws_cloudwatch_event_target" "historical_context_refresh_lambda" {
#   rule      = aws_cloudwatch_event_rule.historical_context_refresh.name
#   target_id = "HistoricalContextRefreshLambda"
#   arn       = aws_lambda_function.historical_context_refresh.arn
# }

# # Lambda permission for EventBridge to invoke
# resource "aws_lambda_permission" "allow_eventbridge_historical_refresh" {
#   statement_id  = "AllowExecutionFromEventBridge"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.historical_context_refresh.function_name
#   principal     = "events.amazonaws.com"
#   source_arn    = aws_cloudwatch_event_rule.historical_context_refresh.arn
# }

# ============================================================================
# Lambda Function for Historical Context Refresh
# ============================================================================

# TODO: Create Lambda function
# resource "aws_lambda_function" "historical_context_refresh" {
#   function_name = "${var.project_name}-historical-context-refresh"
#   role          = aws_iam_role.historical_refresh_lambda_role.arn
#   handler       = "refresh_historical_context.lambda_handler"
#   runtime       = "python3.11"
#   timeout       = 300  # 5 minutes (fetching 90 days of data)
#   memory_size   = 512
#   
#   filename         = "lambda_deployment_package.zip"  # Build separately
#   source_code_hash = filebase64sha256("lambda_deployment_package.zip")
#   
#   environment {
#     variables = {
#       ENVIRONMENT = var.environment
#       DYNAMODB_ENDPOINT = ""  # Use AWS DynamoDB
#     }
#   }
#   
#   tags = {
#     Name        = "${var.project_name}-historical-refresh-lambda"
#     Project     = var.project_name
#     Environment = var.environment
#     ManagedBy   = "Terraform"
#   }
# }

# # IAM role for Lambda
# resource "aws_iam_role" "historical_refresh_lambda_role" {
#   name = "${var.project_name}-historical-refresh-lambda-role"
#   
#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [{
#       Action = "sts:AssumeRole"
#       Effect = "Allow"
#       Principal = {
#         Service = "lambda.amazonaws.com"
#       }
#     }]
#   })
#   
#   tags = {
#     Name        = "${var.project_name}-historical-refresh-lambda-role"
#     Project     = var.project_name
#     Environment = var.environment
#     ManagedBy   = "Terraform"
#   }
# }

# # IAM policy for Lambda to access DynamoDB and CloudWatch Logs
# resource "aws_iam_role_policy" "historical_refresh_lambda_policy" {
#   name = "${var.project_name}-historical-refresh-lambda-policy"
#   role = aws_iam_role.historical_refresh_lambda_role.id
#   
#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Effect = "Allow"
#         Action = [
#           "dynamodb:PutItem",
#           "dynamodb:GetItem",
#           "dynamodb:UpdateItem"
#         ]
#         Resource = aws_dynamodb_table.market_context_cache.arn
#       },
#       {
#         Effect = "Allow"
#         Action = [
#           "logs:CreateLogGroup",
#           "logs:CreateLogStream",
#           "logs:PutLogEvents"
#         ]
#         Resource = "arn:aws:logs:*:*:*"
#       }
#     ]
#   })
# }

# ============================================================================
# NOTES:
# ============================================================================
# 
# DEPLOYMENT STEPS:
# 
# 1. Build Lambda deployment package:
#    cd app/backend/scripts
#    pip install -t ./package pandas numpy aiohttp
#    cd package && zip -r ../lambda_deployment_package.zip .
#    cd .. && zip -g lambda_deployment_package.zip refresh_historical_context.py
#    mv lambda_deployment_package.zip ../../../infra/
# 
# 2. Uncomment all resources in this file
# 
# 3. Deploy:
#    cd infra
#    terraform apply
# 
# 4. Test manually:
#    aws lambda invoke --function-name tradepulse-historical-context-refresh \
#      --region eu-west-2 response.json
# 
# 5. Verify in DynamoDB:
#    aws dynamodb get-item --table-name market_context_cache \
#      --key '{"symbol":{"S":"BTCUSDT"},"period":{"S":"90D"}}' \
#      --region eu-west-2
# 
# ============================================================================
