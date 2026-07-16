# TradePulse serverless paper bot (M2) — additive, independent stack.
#
# Deliberately a SEPARATE Terraform root from infra/ (the App Runner stack):
# different lifecycle, near-zero cost, and applying infra/ as committed would
# destructively rename tables. This stack is: one DynamoDB table, one zip
# Lambda, one daily EventBridge schedule, one error alarm. ~$0/month.
#
# State: local for now (bootstrap without a state bucket). Migrate to the
# S3 backend once the bucket exists:
#   terraform init -migrate-state \
#     -backend-config="bucket=tradepulse-terraform-state-590183672693" \
#     -backend-config="key=serverless/terraform.tfstate"

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "tradepulse"
      Stack     = "serverless-paper-bot"
      ManagedBy = "terraform"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "eu-west-2"
}

variable "alert_email" {
  description = "Email for Lambda failure alerts (SNS subscription must be confirmed)"
  type        = string
  default     = "krisgrzepka@gmail.com"
}

variable "lambda_zip_path" {
  type    = string
  default = "../dist/paper_bot_lambda.zip"
}

# AWS managed pandas/numpy layer for python3.11 in eu-west-2
variable "pandas_layer_arn" {
  type    = string
  default = "arn:aws:lambda:eu-west-2:336392948345:layer:AWSSDKPandas-Python311:21"
}

locals {
  function_name = "tradepulse-paper-bot"
  table_name    = "tradepulse_paper_bot"
}

# ---------------------------------------------------------------- DynamoDB --
# State + decision log, single on-demand table:
#   pk = "<symbol>_<timeframe>", sk = "state" | "decision#<bar>"
resource "aws_dynamodb_table" "paper_bot" {
  name         = local.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

# ------------------------------------------------------------------ Lambda --
resource "aws_iam_role" "lambda_exec" {
  name = "${local.function_name}-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${local.function_name}-dynamodb"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
      ]
      Resource = aws_dynamodb_table.paper_bot.arn
    }]
  })
}

resource "aws_lambda_function" "paper_bot" {
  function_name = local.function_name
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.11"
  handler       = "app.backend.paper_trading.lambda_handler.handler"
  filename      = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  timeout       = 120
  memory_size   = 512
  architectures = ["x86_64"]

  layers = [var.pandas_layer_arn]

  environment {
    variables = {
      PAPER_STATE_BACKEND = "dynamodb"
      PAPER_STATE_TABLE   = aws_dynamodb_table.paper_bot.name
      TRADING_SYMBOL      = "BTCUSDT"
      TRADING_TIMEFRAME   = "1d"
    }
  }
}

resource "aws_cloudwatch_log_group" "paper_bot" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 30
}

# --------------------------------------------------------------- Scheduler --
# Daily, 00:10 UTC — shortly after the 1d bar close. The step is idempotent
# per bar, so a retry can never double-trade.
resource "aws_iam_role" "scheduler" {
  name = "${local.function_name}-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  name = "${local.function_name}-invoke"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.paper_bot.arn
    }]
  })
}

resource "aws_scheduler_schedule" "daily_step" {
  name                = "${local.function_name}-daily"
  schedule_expression = "cron(10 0 * * ? *)"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.paper_bot.arn
    role_arn = aws_iam_role.scheduler.arn

    retry_policy {
      maximum_retry_attempts       = 3
      maximum_event_age_in_seconds = 3600
    }
  }
}

# ------------------------------------------------- Status endpoint (❓D7) --
# Read-only public status page/JSON — one user, paper data, no secrets.
resource "aws_iam_role" "status_exec" {
  name = "${local.function_name}-status-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "status_logs" {
  role       = aws_iam_role.status_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "status_dynamodb_read" {
  name = "${local.function_name}-status-read"
  role = aws_iam_role.status_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:Query"]
      Resource = aws_dynamodb_table.paper_bot.arn
    }]
  })
}

resource "aws_lambda_function" "status" {
  function_name    = "${local.function_name}-status"
  role             = aws_iam_role.status_exec.arn
  runtime          = "python3.11"
  handler          = "app.backend.paper_trading.status_handler.handler"
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  timeout          = 15
  memory_size      = 256
  architectures    = ["x86_64"]

  # the paper_trading package pulls pandas via its __init__ import chain
  layers = [var.pandas_layer_arn]

  environment {
    variables = {
      PAPER_STATE_TABLE = aws_dynamodb_table.paper_bot.name
      PAPER_STATE_PK    = "BTCUSDT_1d"
    }
  }
}

resource "aws_lambda_function_url" "status" {
  function_name      = aws_lambda_function.status.function_name
  authorization_type = "NONE"
}

# auth NONE still requires an explicit public-invoke resource policy.
# Since Oct 2025 AWS requires BOTH InvokeFunctionUrl AND InvokeFunction
# in the policy for public URLs — with only the former the URL 403s.
resource "aws_lambda_permission" "status_public" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.status.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

# NOTE (2026-07-16): since Oct 2025 public function URLs ALSO require a
# lambda:InvokeFunction statement with the InvokedViaFunctionUrl condition
# (docs/lambda/urls-auth). AWS provider 5.x cannot express that condition
# (invoked_via_function_url lands in provider 6.x), so the statement was
# added OUT OF BAND via the API:
#   add_permission(StatementId="AllowPublicFunctionUrlInvoke",
#                  Action="lambda:InvokeFunction", Principal="*",
#                  InvokedViaFunctionUrl=True)
# TODO: fold into Terraform when upgrading to provider ~> 6.0.

resource "aws_cloudwatch_log_group" "status" {
  name              = "/aws/lambda/${local.function_name}-status"
  retention_in_days = 14
}

output "status_url" {
  value = aws_lambda_function_url.status.function_url
}

# ------------------------------------------------------------------ Alarm --
resource "aws_sns_topic" "alerts" {
  name = "${local.function_name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${local.function_name}-errors"
  alarm_description   = "Paper bot Lambda failed — check CloudWatch logs"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.paper_bot.function_name }
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

# ---------------------------------------------------------------- Outputs --
output "lambda_function_name" {
  value = aws_lambda_function.paper_bot.function_name
}

output "dynamodb_table" {
  value = aws_dynamodb_table.paper_bot.name
}

output "schedule" {
  value = aws_scheduler_schedule.daily_step.schedule_expression
}
