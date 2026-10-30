# Kraken paper channel (2026-10-30) — the bot that will trade real money on
# Kraken, run first on paper. XBT/GBP daily candles from Kraken's public API,
# 0.80% taker fee, half the account with the rebalance band, F7 and the account
# kill switch. Rules: docs/KRAKEN_PILOT_PREREGISTRATION_2026-10-30.md; the map of
# accounts and resources: KRAKEN.md.
#
# Its own Lambda, role, zip, schedule, DLQ and alarms, like the shadow and venue
# channels. Shared read-only references only: the DynamoDB table (partition key
# "XBTGBP_1d") and the SNS alert topic. No credentials: paper needs none.
#
# ⚠️ Its own zip for the same reason as the shadow's: reusing var.lambda_zip_path
# would change the M5 bot's source hash and redeploy it.

variable "kraken_paper_lambda_zip_path" {
  description = "Zip for the Kraken paper channel. MUST differ from lambda_zip_path."
  type        = string
  default     = "../dist/kraken_paper_lambda.zip"
}

variable "kraken_paper_capital" {
  description = "Virtual GBP the paper book starts with (pre-registered: 200)."
  type        = number
  default     = 200
}

locals {
  kraken_paper_function_name = "tradepulse-paper-kraken"
}

# ------------------------------------------------------------------- Lambda --
resource "aws_iam_role" "kraken_paper_exec" {
  name = "${local.kraken_paper_function_name}-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "kraken_paper_logs" {
  role       = aws_iam_role.kraken_paper_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "kraken_paper_dynamodb" {
  name = "${local.kraken_paper_function_name}-dynamodb"
  role = aws_iam_role.kraken_paper_exec.id

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

# Only the dead-man URL, and only this channel's. Paper holds no keys.
resource "aws_iam_role_policy" "kraken_paper_ssm" {
  name = "${local.kraken_paper_function_name}-ssm"
  role = aws_iam_role.kraken_paper_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameter"]
      Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.healthcheck_param_prefix}/paper-kraken"
    }]
  })
}

resource "aws_lambda_function" "kraken_paper" {
  function_name    = local.kraken_paper_function_name
  role             = aws_iam_role.kraken_paper_exec.arn
  runtime          = "python3.11"
  handler          = "app.backend.paper_trading.kraken_paper_handler.handler"
  filename         = var.kraken_paper_lambda_zip_path
  source_code_hash = filebase64sha256(var.kraken_paper_lambda_zip_path)
  timeout          = 60
  memory_size      = 256
  architectures    = ["x86_64"]

  # One writer at a time on the book.
  reserved_concurrent_executions = 1

  layers = [var.pandas_layer_arn]

  environment {
    variables = {
      PAPER_STATE_BACKEND = "dynamodb"
      PAPER_STATE_TABLE   = aws_dynamodb_table.paper_bot.name
      TRADING_SYMBOL      = "XBTGBP"
      PAPER_CAPITAL       = tostring(var.kraken_paper_capital)
      HEALTHCHECK_PARAM   = "${var.healthcheck_param_prefix}/paper-kraken"
    }
  }
}

# Retries belong to the scheduler (3 attempts, DLQ behind them); the step is
# idempotent per bar, so a retry can never trade twice.
resource "aws_lambda_function_event_invoke_config" "kraken_paper" {
  function_name          = aws_lambda_function.kraken_paper.function_name
  maximum_retry_attempts = 0
}

resource "aws_cloudwatch_log_group" "kraken_paper" {
  name              = "/aws/lambda/${local.kraken_paper_function_name}"
  retention_in_days = 30
}

# ---------------------------------------------------------------- Scheduler --
# 00:10 UTC: Kraken's daily candle closes at 00:00 UTC.
resource "aws_iam_role" "kraken_paper_scheduler" {
  name = "${local.kraken_paper_function_name}-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "kraken_paper_scheduler_invoke" {
  name = "${local.kraken_paper_function_name}-invoke"
  role = aws_iam_role.kraken_paper_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.kraken_paper.arn
    }]
  })
}

resource "aws_sqs_queue" "kraken_paper_scheduler_dlq" {
  name                      = "${local.kraken_paper_function_name}-scheduler-dlq"
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_iam_role_policy" "kraken_paper_scheduler_dlq" {
  name = "${local.kraken_paper_function_name}-dlq"
  role = aws_iam_role.kraken_paper_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "sqs:SendMessage"
      Resource = aws_sqs_queue.kraken_paper_scheduler_dlq.arn
    }]
  })
}

resource "aws_scheduler_schedule" "kraken_paper_daily" {
  name                = "${local.kraken_paper_function_name}-daily"
  schedule_expression = "cron(10 0 * * ? *)"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.kraken_paper.arn
    role_arn = aws_iam_role.kraken_paper_scheduler.arn

    retry_policy {
      maximum_retry_attempts       = 3
      maximum_event_age_in_seconds = 3600
    }

    dead_letter_config {
      arn = aws_sqs_queue.kraken_paper_scheduler_dlq.arn
    }
  }
}

# ------------------------------------------------------------------- Alarms --
# Period 300, not a day: see the reasoning on shadow_errors in shadow.tf.
resource "aws_cloudwatch_metric_alarm" "kraken_paper_errors" {
  alarm_name          = "${local.kraken_paper_function_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.kraken_paper.function_name
  }

  alarm_description = "Kraken paper channel failed — a missed day breaks P1 (28 days without errors) before the pilot."
  alarm_actions     = [aws_sns_topic.alerts.arn]
}

# 25 empty hourly buckets = the 00:10 UTC run did not happen (see shadow.tf).
resource "aws_cloudwatch_metric_alarm" "kraken_paper_heartbeat" {
  alarm_name          = "${local.kraken_paper_function_name}-no-invocation"
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
    FunctionName = aws_lambda_function.kraken_paper.function_name
  }

  alarm_description = "Kraken paper channel has not run for >24h."
  alarm_actions     = [aws_sns_topic.alerts.arn]
  ok_actions        = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "kraken_paper_scheduler_dlq" {
  alarm_name          = "${local.kraken_paper_function_name}-dlq"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.kraken_paper_scheduler_dlq.name
  }

  alarm_description = "Kraken paper schedule could not deliver — the channel is not running."
  alarm_actions     = [aws_sns_topic.alerts.arn]
}

# A halt returns 200 and moves no error metric; this is what publishes it.
resource "aws_cloudwatch_log_metric_filter" "kraken_paper_killswitch" {
  name           = "${local.kraken_paper_function_name}-killswitch"
  log_group_name = aws_cloudwatch_log_group.kraken_paper.name
  pattern        = "\"KILL SWITCH:\""

  metric_transformation {
    name          = "KillSwitchHalts"
    namespace     = "TradePulse/paper-kraken"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_metric_alarm" "kraken_paper_killswitch" {
  alarm_name          = "${local.kraken_paper_function_name}-killswitch"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "KillSwitchHalts"
  namespace           = "TradePulse/paper-kraken"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  alarm_description = "Kraken paper channel HALTED — the account fell 25% from its peak (or 15% in a bar). It does not re-arm itself."
  alarm_actions     = [aws_sns_topic.alerts.arn]
}

output "kraken_paper_function_name" {
  value = aws_lambda_function.kraken_paper.function_name
}
