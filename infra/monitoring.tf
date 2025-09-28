# CloudWatch monitoring and alarms for TradePulse.AI

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "tradepulse" {
  count = var.enable_monitoring ? 1 : 0
  
  dashboard_name = "${var.project_name}-${var.environment}"

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
            ["AWS/AppRunner", "RequestCount", "ServiceName", "${var.project_name}-backend"],
            [".", "ResponseTime", ".", "."],
            [".", "ActiveInstances", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.region
          title   = "App Runner Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.project_name}_signals"],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
            [".", "ThrottledRequests", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.region
          title   = "DynamoDB Metrics - Signals Table"
          period  = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '/aws/apprunner/${var.project_name}-backend'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 100"
          region  = var.region
          title   = "Recent Errors"
          view    = "table"
        }
      }
    ]
  })
}

# App Runner Alarms
resource "aws_cloudwatch_metric_alarm" "app_runner_high_response_time" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-high-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ResponseTime"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Average"
  threshold           = "5000"  # 5 seconds
  alarm_description   = "This metric monitors app runner response time"
  # alarm_actions = []  # No SNS - alarms visible in CloudWatch console

  dimensions = {
    ServiceName = "${var.project_name}-backend"
  }

  tags = {
    Name = "${var.project_name}-high-response-time-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "app_runner_high_error_rate" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4xxStatusResponses"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors app runner 4xx errors"
  # alarm_actions = []  # No SNS - alarms visible in CloudWatch console

  dimensions = {
    ServiceName = "${var.project_name}-backend"
  }

  tags = {
    Name = "${var.project_name}-high-error-rate-alarm"
  }
}

# DynamoDB Alarms
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttled_requests" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-dynamodb-throttled"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors DynamoDB throttled requests"
  # alarm_actions = []  # No SNS - alarms visible in CloudWatch console

  dimensions = {
    TableName = "${var.project_name}_signals"
  }

  tags = {
    Name = "${var.project_name}-dynamodb-throttled-alarm"
  }
}

# SNS removed for cost optimization - alarms visible in CloudWatch console
# Add SNS back later if email/SMS notifications needed

# CloudWatch Log Insights Queries (saved)
resource "aws_cloudwatch_query_definition" "trading_signals" {
  count = var.enable_monitoring ? 1 : 0
  
  name = "${var.project_name}/trading-signals"

  log_group_names = [
    "/aws/apprunner/${var.project_name}-backend"
  ]

  query_string = <<EOF
fields @timestamp, @message
| filter @message like /UNIFIED Signal Generated/
| parse @message /confidence=(?<confidence>\d+\.\d+)/
| parse @message /action=(?<action>\w+)/
| stats count() by action
| sort count desc
EOF
}

resource "aws_cloudwatch_query_definition" "trading_errors" {
  count = var.enable_monitoring ? 1 : 0
  
  name = "${var.project_name}/trading-errors"

  log_group_names = [
    "/aws/apprunner/${var.project_name}-backend"
  ]

  query_string = <<EOF
fields @timestamp, @message
| filter @message like /ERROR/ or @message like /CRITICAL/
| sort @timestamp desc
| limit 100
EOF
}

resource "aws_cloudwatch_query_definition" "websocket_health" {
  count = var.enable_monitoring ? 1 : 0
  
  name = "${var.project_name}/websocket-health"

  log_group_names = [
    "/aws/apprunner/${var.project_name}-backend"
  ]

  query_string = <<EOF
fields @timestamp, @message
| filter @message like /WebSocket/ or @message like /Connecting to/ or @message like /reconnect/
| sort @timestamp desc
| limit 50
EOF
}

# Custom CloudWatch Metrics (for application-specific metrics)
resource "aws_cloudwatch_log_metric_filter" "trading_signals_generated" {
  count = var.enable_monitoring ? 1 : 0
  
  name           = "${var.project_name}-signals-generated"
  log_group_name = "/aws/apprunner/${var.project_name}-backend"
  pattern        = "UNIFIED Signal Generated"

  metric_transformation {
    name      = "SignalsGenerated"
    namespace = "TradePulse.AI"
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "trading_errors" {
  count = var.enable_monitoring ? 1 : 0
  
  name           = "${var.project_name}-trading-errors"
  log_group_name = "/aws/apprunner/${var.project_name}-backend"
  pattern        = "ERROR"

  metric_transformation {
    name      = "TradingErrors"
    namespace = "TradePulse.AI"
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "websocket_reconnections" {
  count = var.enable_monitoring ? 1 : 0
  
  name           = "${var.project_name}-websocket-reconnections"
  log_group_name = "/aws/apprunner/${var.project_name}-backend"
  pattern        = "Reconnecting"

  metric_transformation {
    name      = "WebSocketReconnections"
    namespace = "TradePulse.AI"
    value     = "1"
  }
}

# Brain Controller heartbeat monitoring
resource "aws_cloudwatch_log_metric_filter" "brain_heartbeat" {
  count = var.enable_monitoring ? 1 : 0
  
  name           = "${var.project_name}-brain-heartbeat"
  log_group_name = "/aws/apprunner/${var.project_name}-backend"
  pattern        = "Acquired trading brain lease"

  metric_transformation {
    name      = "BrainControllerHeartbeat"
    namespace = "TradePulse.AI"
    value     = "1"
  }
}

# Alarm for missing brain controller heartbeat (improved with your suggestions)
resource "aws_cloudwatch_metric_alarm" "brain_controller_down" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-brain-missing-heartbeat"
  comparison_operator = "LessThanOrEqualToThreshold"
  evaluation_periods  = "3"
  metric_name         = "BrainHeartbeat"
  namespace           = "TradePulse/Brain"
  dimensions = {
    Service = "${var.project_name}-backend"
  }
  statistic           = "Sum"
  period              = "60"
  threshold           = "0"
  alarm_description   = "No BrainHeartbeat for >3 minutes"
  # alarm_actions = []  # No SNS - alarms visible in CloudWatch console
  treat_missing_data  = "breaching"   # Missing data = alarm

  tags = {
    Name = "${var.project_name}-brain-missing-heartbeat-alarm"
  }
}
