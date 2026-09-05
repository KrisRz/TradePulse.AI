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

variable "venue_credentials_path" {
  description = <<-EOT
    SSM prefix holding the credentials for the STRATEGY channel (venue-4h).

    Points at the shared demo prefix today. The 2026-09-04 audit (HIGH-3) asks
    for one key per bot before real money: two channels reading one secret means
    one leak is two compromised bots, and the heartbeat's key does not need
    permission to move a real position. Flipping this is a deploy, not a code
    change — create the parameters out of band first, exactly as above:

      aws ssm put-parameter --name /tradepulse/venue/key    --type SecureString --value '...'
      aws ssm put-parameter --name /tradepulse/venue/secret --type SecureString --value '...'
  EOT
  type        = string
  default     = "/tradepulse/demo"
}

variable "binance_base_url" {
  description = <<-EOT
    Exchange REST endpoint the executing channels talk to.

    Configuration rather than a constant in a module named "demo": the day this
    points at api.binance.com must be a deploy someone decided on, visible in a
    plan, and not an edit buried in Python.
  EOT
  type        = string
  default     = "https://demo-api.binance.com"
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
  memory_size      = 256
  architectures    = ["x86_64"]

  # One writer at a time: the heartbeat records a stranded position in the same
  # item it reads, and two overlapping runs could each open a leg.
  reserved_concurrent_executions = 1

  # Required even though this path never runs the strategy: importing anything
  # under `app.backend.paper_trading` executes the package __init__, which pulls
  # in `bot` and therefore pandas. Reasoning "the heartbeat does not need pandas"
  # is how this first deploy failed with Runtime.ImportModuleError — the import
  # chain decides, not the call graph. `status` carries the layer for the same
  # reason (see its comment in main.tf).
  layers = [var.pandas_layer_arn]

  environment {
    variables = {
      PAPER_STATE_BACKEND     = "dynamodb"
      PAPER_STATE_TABLE       = aws_dynamodb_table.paper_bot.name
      TRADING_SYMBOL          = "BTCUSDT"
      TRADING_TIMEFRAME       = "1d"
      SHADOW_NOTIONAL         = tostring(var.shadow_notional)
      SHADOW_CREDENTIALS_PATH = var.shadow_credentials_path
      BINANCE_BASE_URL        = var.binance_base_url
    }
  }
}

# Retries belong to the scheduler (3 attempts, DLQ behind them). See the same
# resource in venue_4h.tf for why the Lambda's own layer is turned off.
resource "aws_lambda_function_event_invoke_config" "shadow_bot" {
  function_name          = aws_lambda_function.shadow_bot.function_name
  maximum_retry_attempts = 0
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
#
# The period is 300, NOT the daily invocation interval. A period as long as the
# schedule looks natural and is a trap: CloudWatch evaluates a metric alarm once
# per period, so a day-long window (a) delays the mail by up to a day and (b) —
# the real damage — leaves the alarm already in ALARM when the NEXT day's run
# fails, and a state that does not transition sends no mail. A heartbeat broken
# for a week would mail exactly once, indistinguishable from a one-off. With a
# short window the idle buckets carry no datapoint, notBreaching returns the
# alarm to OK within minutes, and every new failure is its own transition and
# its own mail. Lit-for-24h is not the durable record anyway — the logs are.
resource "aws_cloudwatch_metric_alarm" "shadow_errors" {
  alarm_name          = "${local.shadow_function_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.shadow_bot.function_name
  }

  alarm_description = "Execution path to the demo venue is broken — fix BEFORE M6 needs it."
  alarm_actions     = [aws_sns_topic.alerts.arn]
}

# An Errors alarm cannot see a heartbeat that stopped being invoked at all — a
# disabled schedule or a broken scheduler role emits no Errors datapoint, it
# emits nothing. The heartbeat exists so the execution path cannot rot
# unnoticed; a heartbeat that silently stops running defeats it exactly like a
# failing one. Same shape as the paper bot's alarm in main.tf: Lambda publishes
# no Invocations datapoint in idle hours, so missing data must count as
# breaching, and 25 consecutive empty hourly buckets mean the 00:25 UTC run did
# not happen (that invocation always lands inside a 25h window).
resource "aws_cloudwatch_metric_alarm" "shadow_heartbeat" {
  alarm_name          = "${local.shadow_function_name}-no-invocation"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 25
  datapoints_to_alarm = 25
  metric_name         = "Invocations"
  namespace           = "AWS/Lambda"
  period              = 3600
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "breaching"

  dimensions = {
    FunctionName = aws_lambda_function.shadow_bot.function_name
  }

  alarm_description = "Shadow heartbeat has not run for >24h — the execution path is no longer being exercised."
  alarm_actions     = [aws_sns_topic.alerts.arn]
  ok_actions        = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "shadow_scheduler_dlq" {
  alarm_name          = "${local.shadow_function_name}-dlq"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
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
