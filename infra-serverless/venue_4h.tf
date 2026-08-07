# BTC 4h channel — a paper book whose fills come from a real matching engine.
#
# What it is for, stated honestly.
# The 4h channel was originally justified as "7.2x faster proof". That was
# WRONG, and the correction is load-bearing enough to repeat here: the precision
# of an annualised Sharpe depends on CALENDAR SPAN, not on how finely the span is
# sliced. Simulated 2026-08-06 over 20k histories — SE(4h)/SE(1d) is 1.00x, not
# sqrt(6). Trading more often does not shorten the road to a profitability
# verdict.
#
# What it does buy is the thing 1d structurally cannot. The live channel produces
# 1.69 round-trips a YEAR; this one produces about twelve, each a real signed
# order against a real book. Slippage, fee drag, partial fills and lot rounding
# converge with the number of TRADES, and those are precisely the quantities M6
# depends on. The shadow bot proves the path still works; this measures what it
# costs when a strategy rather than a heartbeat is driving.
#
# ⚠️ SEPARATE FROM EVERY M5 RESOURCE, same discipline as the shadow bot: own
# Lambda, role, schedule, DLQ and alarms; own zip (sharing var.lambda_zip_path
# would redeploy the M5 bot mid-window). Shares only the DynamoDB table — under
# partition key "BTCUSDT_4h", so the measured 1d book is untouchable — and the
# SNS topic.

variable "venue_4h_zip_path" {
  description = "Zip for the 4h venue channel. MUST differ from lambda_zip_path while the M5 window is open."
  type        = string
  default     = "../dist/venue_4h_lambda.zip"
}

variable "venue_4h_max_notional" {
  description = <<-EOT
    Ceiling per order in quote units, and also the book's capital.

    The two are deliberately kept equal: the book sizes positions as a fraction
    of equity, so a "full equity" position must map onto an order of roughly the
    same size at the venue. Let them drift apart and the book would report a
    strategy sitting 99% in cash while the venue held a token position.

    200 USDT mirrors the size M6 actually plans ($50-100 real), leaves the demo
    account's 5000 USDT room for the shadow bot, and keeps every order well clear
    of the 5 USDT MIN_NOTIONAL floor.
  EOT
  type        = number
  default     = 200
}

locals {
  venue_4h_function_name = "tradepulse-venue-4h"
}

# ------------------------------------------------------------------- Lambda --
resource "aws_iam_role" "venue_4h_exec" {
  name = "${local.venue_4h_function_name}-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "venue_4h_logs" {
  role       = aws_iam_role.venue_4h_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "venue_4h_dynamodb" {
  name = "${local.venue_4h_function_name}-dynamodb"
  role = aws_iam_role.venue_4h_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"]
      Resource = aws_dynamodb_table.paper_bot.arn
    }]
  })
}

resource "aws_iam_role_policy" "venue_4h_ssm" {
  name = "${local.venue_4h_function_name}-ssm"
  role = aws_iam_role.venue_4h_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameter", "ssm:GetParameters"]
      Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.shadow_credentials_path}/*"
    }]
  })
}

resource "aws_lambda_function" "venue_4h" {
  function_name    = local.venue_4h_function_name
  role             = aws_iam_role.venue_4h_exec.arn
  runtime          = "python3.11"
  handler          = "app.backend.paper_trading.venue_handler.handler"
  filename         = var.venue_4h_zip_path
  source_code_hash = filebase64sha256(var.venue_4h_zip_path)
  timeout          = 120
  memory_size      = 512 # runs the strategy, so pandas is on the hot path
  architectures    = ["x86_64"]

  # Required: importing anything under app.backend.paper_trading executes the
  # package __init__, which pulls in `bot` and therefore pandas. This one needs
  # it for real, not merely as an import-chain artefact.
  layers = [var.pandas_layer_arn]

  environment {
    variables = {
      PAPER_STATE_BACKEND     = "dynamodb"
      PAPER_STATE_TABLE       = aws_dynamodb_table.paper_bot.name
      TRADING_SYMBOL          = "BTCUSDT"
      TRADING_TIMEFRAME       = "4h"
      VENUE_MAX_NOTIONAL      = tostring(var.venue_4h_max_notional)
      PAPER_CAPITAL           = tostring(var.venue_4h_max_notional)
      SHADOW_CREDENTIALS_PATH = var.shadow_credentials_path
    }
  }
}

resource "aws_cloudwatch_log_group" "venue_4h" {
  name              = "/aws/lambda/${local.venue_4h_function_name}"
  retention_in_days = 30
}

# ---------------------------------------------------------------- Scheduler --
# 4h bars close at 00/04/08/12/16/20 UTC; run ten minutes after each, matching
# the 1d bot's habit of letting the bar settle before reading it. The step is
# idempotent per bar (`last_bar`), so a retry cannot double-trade.
resource "aws_iam_role" "venue_4h_scheduler" {
  name = "${local.venue_4h_function_name}-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "venue_4h_scheduler_invoke" {
  name = "${local.venue_4h_function_name}-invoke"
  role = aws_iam_role.venue_4h_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.venue_4h.arn
    }]
  })
}

resource "aws_sqs_queue" "venue_4h_dlq" {
  name                      = "${local.venue_4h_function_name}-scheduler-dlq"
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_iam_role_policy" "venue_4h_scheduler_dlq" {
  name = "${local.venue_4h_function_name}-dlq"
  role = aws_iam_role.venue_4h_scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "sqs:SendMessage"
      Resource = aws_sqs_queue.venue_4h_dlq.arn
    }]
  })
}

resource "aws_scheduler_schedule" "venue_4h" {
  name                = "${local.venue_4h_function_name}-schedule"
  schedule_expression = "cron(10 0,4,8,12,16,20 * * ? *)"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.venue_4h.arn
    role_arn = aws_iam_role.venue_4h_scheduler.arn

    retry_policy {
      maximum_retry_attempts       = 3
      maximum_event_age_in_seconds = 3600
    }

    dead_letter_config {
      arn = aws_sqs_queue.venue_4h_dlq.arn
    }
  }
}

# ------------------------------------------------------------------- Alarms --
# This channel places real orders and can HOLD a position for weeks. A silent
# failure between the entry and the exit would strand it, so errors must be loud.
#
# The period is 300, not one 4h bar: CloudWatch evaluates once per period, so a
# bar-long window would leave the alarm already lit when the NEXT bar fails, and
# a state that does not transition sends no mail — consecutive failures, the
# case that actually strands a position, would mail once. See the longer note in
# shadow.tf.
resource "aws_cloudwatch_metric_alarm" "venue_4h_errors" {
  alarm_name          = "${local.venue_4h_function_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.venue_4h.function_name
  }

  alarm_description = "4h venue channel failed — it may be holding a position it cannot close."
  alarm_actions     = [aws_sns_topic.alerts.arn]
}

# The failure this channel cannot afford is the one no Errors datapoint reports:
# the schedule stops firing while a real position is open, so nothing ever
# evaluates the exit and the position sits at the venue indefinitely. Bars run
# 6x/day at :10, so between two runs at most three hourly buckets are empty
# (01:00, 02:00, 03:00 between the 00:10 and 04:10 runs) — five consecutive
# empty buckets cannot happen unless a bar was genuinely missed.
resource "aws_cloudwatch_metric_alarm" "venue_4h_heartbeat" {
  alarm_name          = "${local.venue_4h_function_name}-no-invocation"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 5
  datapoints_to_alarm = 5
  metric_name         = "Invocations"
  namespace           = "AWS/Lambda"
  period              = 3600
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "breaching"

  dimensions = {
    FunctionName = aws_lambda_function.venue_4h.function_name
  }

  alarm_description = "4h venue channel missed a bar — the schedule is not firing while a position may be open."
  alarm_actions     = [aws_sns_topic.alerts.arn]
  ok_actions        = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "venue_4h_dlq" {
  alarm_name          = "${local.venue_4h_function_name}-dlq"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.venue_4h_dlq.name
  }

  alarm_description = "4h schedule could not deliver — bars are being missed."
  alarm_actions     = [aws_sns_topic.alerts.arn]
}

output "venue_4h_function_name" {
  value = aws_lambda_function.venue_4h.function_name
}
