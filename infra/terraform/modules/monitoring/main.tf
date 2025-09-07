# Data source to get current AWS region
data "aws_region" "current" {}

# CloudWatch Dashboard for Trading Operations
resource "aws_cloudwatch_dashboard" "trading_overview" {
  dashboard_name = "${var.app_name}-${var.env}-trading-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "${var.app_name}-${var.env}-ai-inference"],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."],
            [".", "Throttles", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "AI Inference Lambda Performance"
          period  = 300
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGatewayV2", "IntegrationLatency", "ApiId", var.websocket_api_id],
            [".", "Count", ".", "."],
            [".", "4XXError", ".", "."],
            [".", "5XXError", ".", "."]
          ]
          view   = "timeSeries"
          region = data.aws_region.current.name
          title  = "WebSocket API Performance"
          period = 300
          stat   = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.app_name}-${var.env}-table"],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            [".", "ThrottledRequests", ".", "."]
          ]
          view   = "timeSeries"
          region = data.aws_region.current.name
          title  = "DynamoDB Performance"
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/States", "ExecutionTime", "StateMachineArn", var.ai_pipeline_arn],
            [".", "ExecutionsFailed", ".", "."],
            [".", "ExecutionsSucceeded", ".", "."]
          ]
          view   = "timeSeries"
          region = data.aws_region.current.name
          title  = "AI Pipeline Step Functions"
          period = 300
          stat   = "Average"
        }
      },
      {
        type   = "log"
        x      = 16
        y      = 6
        width  = 8
        height = 6
        properties = {
          query  = "SOURCE '/aws/lambda/${var.app_name}-${var.env}-ai-inference' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 100"
          region = data.aws_region.current.name
          title  = "Recent AI Inference Errors"
          view   = "table"
        }
      }
    ]
  })
}

# SNS Topics for alerts
resource "aws_sns_topic" "critical_alerts" {
  name = "${var.app_name}-${var.env}-critical-alerts"
  tags = var.tags
}

resource "aws_sns_topic" "performance_alerts" {
  name = "${var.app_name}-${var.env}-performance-alerts"
  tags = var.tags
}

# SNS subscriptions (email)
resource "aws_sns_topic_subscription" "critical_email" {
  count     = length(var.alert_emails)
  topic_arn = aws_sns_topic.critical_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_emails[count.index]
}

resource "aws_sns_topic_subscription" "performance_email" {
  count     = length(var.alert_emails)
  topic_arn = aws_sns_topic.performance_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_emails[count.index]
}

# Critical Alerts

# Lambda function errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.app_name}-${var.env}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Lambda function error rate too high"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]

  dimensions = {
    FunctionName = "${var.app_name}-${var.env}-ai-inference"
  }

  tags = var.tags
}

# Lambda function duration (cold starts)
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.app_name}-${var.env}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "30000" # 30 seconds
  alarm_description   = "Lambda function duration too high (possible cold starts)"
  alarm_actions       = [aws_sns_topic.performance_alerts.arn]

  dimensions = {
    FunctionName = "${var.app_name}-${var.env}-ai-inference"
  }

  tags = var.tags
}

# DynamoDB throttling
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  alarm_name          = "${var.app_name}-${var.env}-dynamodb-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "DynamoDB requests being throttled"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]

  dimensions = {
    TableName = "${var.app_name}-${var.env}-table"
  }

  tags = var.tags
}

# WebSocket API errors
resource "aws_cloudwatch_metric_alarm" "websocket_errors" {
  alarm_name          = "${var.app_name}-${var.env}-websocket-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGatewayV2"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "WebSocket API 5XX errors too high"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]

  dimensions = {
    ApiId = var.websocket_api_id
  }

  tags = var.tags
}

# Cost monitoring
resource "aws_budgets_budget" "monthly_cost" {
  name              = "${var.app_name}-${var.env}-monthly-budget"
  budget_type       = "COST"
  limit_amount      = var.monthly_budget_limit
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = "2025-01-01_00:00"

  cost_filter {
    name = "Service"
    values = [
      "Amazon API Gateway",
      "AWS Lambda",
      "Amazon DynamoDB",
      "Amazon CloudFront",
      "AWS Step Functions",
      "Amazon EventBridge"
    ]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.budget_alert_emails
  }
}
