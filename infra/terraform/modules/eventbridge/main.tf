# Custom event bus for trading events
resource "aws_cloudwatch_event_bus" "trading" {
  name = "${var.app_name}-${var.env}-trading-events"
  tags = var.tags
}

# IAM role for EventBridge to invoke targets
resource "aws_iam_role" "eventbridge" {
  name = "${var.app_name}-${var.env}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM policy for EventBridge to invoke Step Functions
resource "aws_iam_role_policy" "eventbridge_stepfunctions" {
  name = "${var.app_name}-${var.env}-eventbridge-stepfunctions-policy"
  role = aws_iam_role.eventbridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = [
          var.ai_pipeline_step_function_arn,
          var.emergency_halt_step_function_arn,
          var.model_retraining_step_function_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = [
          aws_sqs_queue.trading_events.arn,
          aws_sqs_queue.trading_events_dlq.arn
        ]
      }
    ]
  })
}

# Market data updated event rule
resource "aws_cloudwatch_event_rule" "market_data_updated" {
  name           = "${var.app_name}-${var.env}-market-data-updated"
  description    = "Triggered when new Bitcoin market data is received"
  event_bus_name = aws_cloudwatch_event_bus.trading.name

  event_pattern = jsonencode({
    source      = ["tradepulse.market"]
    detail-type = ["Market Data Updated"]
    detail = {
      symbol = ["BTCUSDT"]
      type   = ["price", "candle", "orderbook"]
    }
  })

  tags = var.tags
}

# Trading signal generated event rule
resource "aws_cloudwatch_event_rule" "trading_signal_generated" {
  name           = "${var.app_name}-${var.env}-trading-signal-generated"
  description    = "Triggered when AI generates a trading signal"
  event_bus_name = aws_cloudwatch_event_bus.trading.name

  event_pattern = jsonencode({
    source      = ["tradepulse.ai"]
    detail-type = ["Trading Signal Generated"]
    detail = {
      signal_type = ["BUY", "SELL", "HOLD"]
      confidence  = [{ "numeric" : [">", 0.7] }]
    }
  })

  tags = var.tags
}

# Emergency event rule (high priority)
resource "aws_cloudwatch_event_rule" "emergency_events" {
  name           = "${var.app_name}-${var.env}-emergency-events"
  description    = "Critical emergency events requiring immediate action"
  event_bus_name = aws_cloudwatch_event_bus.trading.name

  event_pattern = jsonencode({
    source      = ["tradepulse.emergency"]
    detail-type = ["Risk Limit Exceeded", "Connection Lost", "Model Error"]
  })

  tags = var.tags
}

# Daily model retraining schedule
resource "aws_cloudwatch_event_rule" "daily_retraining" {
  name                = "${var.app_name}-${var.env}-daily-retraining"
  description         = "Trigger model retraining daily at 2 AM UTC"
  schedule_expression = "cron(0 2 * * ? *)"

  tags = var.tags
}

# Event targets

# Trigger AI pipeline on market data updates
resource "aws_cloudwatch_event_target" "ai_pipeline_trigger" {
  rule           = aws_cloudwatch_event_rule.market_data_updated.name
  event_bus_name = aws_cloudwatch_event_bus.trading.name
  target_id      = "TriggerAIPipeline"
  arn            = var.ai_pipeline_step_function_arn
  role_arn       = aws_iam_role.eventbridge.arn

  input_transformer {
    input_paths = {
      symbol    = "$.detail.symbol"
      price     = "$.detail.price"
      timestamp = "$.detail.timestamp"
    }
    input_template = jsonencode({
      symbol    = "<symbol>"
      price     = "<price>"
      timestamp = "<timestamp>"
      source    = "eventbridge"
    })
  }
}

# Emergency halt on critical events
resource "aws_cloudwatch_event_target" "emergency_halt_trigger" {
  rule           = aws_cloudwatch_event_rule.emergency_events.name
  event_bus_name = aws_cloudwatch_event_bus.trading.name
  target_id      = "TriggerEmergencyHalt"
  arn            = var.emergency_halt_step_function_arn
  role_arn       = aws_iam_role.eventbridge.arn
}

# Daily retraining trigger
resource "aws_cloudwatch_event_target" "retraining_trigger" {
  rule      = aws_cloudwatch_event_rule.daily_retraining.name
  target_id = "TriggerModelRetraining"
  arn       = var.model_retraining_step_function_arn
  role_arn  = aws_iam_role.eventbridge.arn
}

# SQS queue for reliable event processing
resource "aws_sqs_queue" "trading_events" {
  name                      = "${var.app_name}-${var.env}-trading-events"
  delay_seconds             = 0
  max_message_size          = 262144
  message_retention_seconds = 1209600 # 14 days
  receive_wait_time_seconds = 10

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.trading_events_dlq.arn
    maxReceiveCount     = 3
  })

  tags = var.tags
}

# Dead letter queue for failed events
resource "aws_sqs_queue" "trading_events_dlq" {
  name                      = "${var.app_name}-${var.env}-trading-events-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = var.tags
}

# SQS target for reliable processing
resource "aws_cloudwatch_event_target" "sqs_backup" {
  rule           = aws_cloudwatch_event_rule.trading_signal_generated.name
  event_bus_name = aws_cloudwatch_event_bus.trading.name
  target_id      = "SQSBackup"
  arn            = aws_sqs_queue.trading_events.arn
}
