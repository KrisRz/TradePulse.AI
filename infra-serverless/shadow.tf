# Execution heartbeat (shadow bot) — proves the order path still works, daily.
#
# Why it exists: the order path was proven against a real matching engine on
# 2026-08-06 and starts rotting the same day. Keys expire, permissions get
# revoked, filters change. The live strategy trades 1.69 round-trips a YEAR, so
# it will not exercise the path either — the first order after M6 opens could be
# the first in months, with real money on it. This runs a complete round-trip on
# the demo venue every day instead.
#
# ⚠️ DELIBERATELY SEPARATE FROM EVERY M5 RESOURCE.
# Its own Lambda, role, schedule, DLQ and alarm. It shares exactly two things,
# both read-only references that do not modify the M5 stack:
#   * the DynamoDB table  — different partition key ("SHADOW_BTCUSDT_1d")
#   * the SNS alert topic — same inbox for failures
#
# ⚠️ AND ITS OWN ZIP — this is the trap worth spelling out.
# `aws_lambda_function.paper_bot` uses `filename = var.lambda_zip_path` with
# `source_code_hash = filebase64sha256(...)`. If the shadow Lambda reused that
# variable, rebuilding the package to ship the shadow code would change the hash
# and REDEPLOY THE M5 BOT MID-WINDOW — the one thing the paper window forbids.
# So the shadow gets `var.shadow_lambda_zip_path`, and the M5 zip is left alone
# on disk until the window closes.

variable "shadow_lambda_zip_path" {
  description = "Zip for the shadow bot. MUST be a different file from lambda_zip_path while the M5 window is open."
  type        = string
  default     = "../dist/shadow_bot_lambda.zip"
}

variable "shadow_notional" {
  description = "Quote units committed per heartbeat leg. The venue floor is 5 USDT."
  type        = number
  default     = 10
}

variable "shadow_credentials_path" {
  description = <<-EOT
    SSM Parameter Store prefix holding the demo credentials.

    Terraform deliberately does NOT manage the parameter VALUES — a SecureString
    read or written through Terraform lands in plaintext in tfstate. It grants
    read access only; create them out of band, once:

      aws ssm put-parameter --name /tradepulse/demo/key    --type SecureString --value '...'
      aws ssm put-parameter --name /tradepulse/demo/secret --type SecureString --value '...'
  EOT
  type        = string
  default     = "/tradepulse/demo"
}

locals {
  shadow_function_name = "tradepulse-shadow-bot"
}

# ------------------------------------------------------------------- Lambda --
resource "aws_iam_role" "shadow_exec" {
  name = "${local.shadow_function_name}-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "shadow_logs" {
  role       = aws_iam_role.shadow_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "shadow_dynamodb" {
  name = "${local.shadow_function_name}-dynamodb"
  role = aws_iam_role.shadow_exec.id

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

# Read-only, and scoped to this one prefix: the shadow bot can read its own demo
# credentials and nothing else in Parameter Store.
resource "aws_iam_role_policy" "shadow_ssm" {
  name = "${local.shadow_function_name}-ssm"
  role = aws_iam_role.shadow_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameter", "ssm:GetParameters"]
      Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.shadow_credentials_path}/*"
    }]
  })
}

data "aws_caller_identity" "current" {}

resource "aws_lambda_function" "shadow_bot" {
  function_name    = local.shadow_function_name
  role             = aws_iam_role.shadow_exec.arn
  runtime          = "python3.11"
  handler          = "app.backend.paper_trading.shadow_handler.handler"
  filename         = var.shadow_lambda_zip_path
  source_code_hash = filebase64sha256(var.shadow_lambda_zip_path)
  timeout          = 120
  memory_size      = 256 # no pandas on this path — it never touches the strategy
  architectures    = ["x86_64"]

  environment {
    variables = {
      PAPER_STATE_BACKEND     = "dynamodb"
      PAPER_STATE_TABLE       = aws_dynamodb_table.paper_bot.name
      TRADING_SYMBOL          = "BTCUSDT"
      TRADING_TIMEFRAME       = "1d"
      SHADOW_NOTIONAL         = tostring(var.shadow_notional)
      SHADOW_CREDENTIALS_PATH = var.shadow_credentials_path
    }
  }
}

resource "aws_cloudwatch_log_group" "shadow_bot" {
  name              = "/aws/lambda/${local.shadow_function_name}"
  retention_in_days = 30
}

# ---------------------------------------------------------------- Scheduler --
# 00:25 UTC — after the paper bot's 00:10 slot, so the two never write the same
# DynamoDB item at once (they use different keys, but staggering costs nothing).
# The heartbeat is idempotent per UTC day, so a retry cannot double-trade.
resource "aws_iam_role" "shadow_scheduler" {
  name = "${local.shadow_function_name}-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "shadow_scheduler_invoke" {
  name = "${local.shadow_function_name}-invoke"
  role = aws_iam_role.shadow_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.shadow_bot.arn
    }]
  })
}

resource "aws_sqs_queue" "shadow_scheduler_dlq" {
  name                      = "${local.shadow_function_name}-scheduler-dlq"
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_iam_role_policy" "shadow_scheduler_dlq" {
  name = "${local.shadow_function_name}-dlq"
  role = aws_iam_role.shadow_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "sqs:SendMessage"
      Resource = aws_sqs_queue.shadow_scheduler_dlq.arn
    }]
  })
}

resource "aws_scheduler_schedule" "shadow_daily" {
  name                = "${local.shadow_function_name}-daily"
  schedule_expression = "cron(25 0 * * ? *)"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.shadow_bot.arn
    role_arn = aws_iam_role.shadow_scheduler.arn

    retry_policy {
      maximum_retry_attempts       = 3
      maximum_event_age_in_seconds = 3600
    }

    dead_letter_config {
      arn = aws_sqs_queue.shadow_scheduler_dlq.arn
    }
  }
}

# ------------------------------------------------------------------- Alarms --
# The whole point is to learn that execution broke. A silent failure here would
# defeat the exercise, so any error mails the same address as the M5 alarms.
resource "aws_cloudwatch_metric_alarm" "shadow_errors" {
  alarm_name          = "${local.shadow_function_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 86400
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.shadow_bot.function_name
  }

  alarm_description = "Execution path to the demo venue is broken — fix BEFORE M6 needs it."
  alarm_actions     = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "shadow_scheduler_dlq" {
  alarm_name          = "${local.shadow_function_name}-dlq"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 86400
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.shadow_scheduler_dlq.name
  }

  alarm_description = "Shadow schedule could not deliver — the heartbeat is not running."
  alarm_actions     = [aws_sns_topic.alerts.arn]
}

output "shadow_function_name" {
  value = aws_lambda_function.shadow_bot.function_name
}
