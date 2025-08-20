# TradePulse.AI - Monitoring Module
# CloudWatch Alarms, SNS, Lambda Monitoring, Application Monitoring
# Enterprise-grade monitoring and alerting infrastructure

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
    Module = "monitoring"
    Service = "monitoring-alerting"
  })
}

# ============================================================================
# SNS TOPICS FOR NOTIFICATIONS
# ============================================================================

# Main alerting topic
resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"
  
  tags = merge(local.common_tags, {
    Purpose = "main-alerting-topic"
  })
}

# Critical alerts topic (for production issues)
resource "aws_sns_topic" "critical_alerts" {
  count = var.environment == "production" ? 1 : 0
  
  name = "${local.name_prefix}-critical-alerts"
  
  tags = merge(local.common_tags, {
    Purpose = "critical-alerting-topic"
    Severity = "critical"
  })
}

# Application performance topic
resource "aws_sns_topic" "performance" {
  count = var.enable_performance_monitoring ? 1 : 0
  
  name = "${local.name_prefix}-performance"
  
  tags = merge(local.common_tags, {
    Purpose = "performance-monitoring-topic"
  })
}

# ============================================================================
# SNS TOPIC SUBSCRIPTIONS
# ============================================================================

# Email subscriptions for alerts
resource "aws_sns_topic_subscription" "email_alerts" {
  count = length(var.alert_email_addresses)
  
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email_addresses[count.index]
}

# Email subscriptions for critical alerts (production only)
resource "aws_sns_topic_subscription" "critical_email_alerts" {
  count = var.environment == "production" ? length(var.critical_alert_email_addresses) : 0
  
  topic_arn = aws_sns_topic.critical_alerts[0].arn
  protocol  = "email"
  endpoint  = var.critical_alert_email_addresses[count.index]
}

# Slack webhook subscriptions (if provided)
resource "aws_sns_topic_subscription" "slack_alerts" {
  count = var.slack_webhook_url != "" ? 1 : 0
  
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "https"
  endpoint  = var.slack_webhook_url
}

# ============================================================================
# CLOUDWATCH LOG GROUPS
# ============================================================================

# Application logs
resource "aws_cloudwatch_log_group" "application" {
  for_each = var.lambda_functions
  
  name              = "/aws/lambda/${local.name_prefix}-${each.key}"
  retention_in_days = var.log_retention_days
  
  tags = merge(local.common_tags, {
    Function = each.key
    Purpose = "application-logs"
  })
}

# Custom application metrics log group
resource "aws_cloudwatch_log_group" "custom_metrics" {
  count = var.enable_custom_metrics ? 1 : 0
  
  name              = "/aws/lambda/${local.name_prefix}-custom-metrics"
  retention_in_days = var.log_retention_days
  
  tags = merge(local.common_tags, {
    Purpose = "custom-metrics-logs"
  })
}

# ============================================================================
# LAMBDA FUNCTION MONITORING
# ============================================================================

# Lambda Error Rate Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  for_each = var.lambda_functions
  
  alarm_name          = "${local.name_prefix}-${each.key}-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorRate"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = var.lambda_error_rate_threshold
  alarm_description   = "Error rate for ${each.key} Lambda function is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    FunctionName = "${local.name_prefix}-${each.key}"
  }
  
  tags = merge(local.common_tags, {
    Function = each.key
    MetricType = "error-rate"
  })
}

# Lambda Duration Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = var.lambda_functions
  
  alarm_name          = "${local.name_prefix}-${each.key}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = var.lambda_duration_threshold_ms
  alarm_description   = "Duration for ${each.key} Lambda function is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    FunctionName = "${local.name_prefix}-${each.key}"
  }
  
  tags = merge(local.common_tags, {
    Function = each.key
    MetricType = "duration"
  })
}

# Lambda Throttles Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  for_each = var.lambda_functions
  
  alarm_name          = "${local.name_prefix}-${each.key}-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Lambda function ${each.key} is being throttled"
  alarm_actions       = var.environment == "production" ? [aws_sns_topic.critical_alerts[0].arn] : [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    FunctionName = "${local.name_prefix}-${each.key}"
  }
  
  tags = merge(local.common_tags, {
    Function = each.key
    MetricType = "throttles"
    Severity = "critical"
  })
}

# Lambda Concurrent Executions Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_concurrent_executions" {
  for_each = var.lambda_functions
  
  alarm_name          = "${local.name_prefix}-${each.key}-concurrent-executions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ConcurrentExecutions"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Maximum"
  threshold           = var.lambda_concurrent_executions_threshold
  alarm_description   = "Concurrent executions for ${each.key} Lambda function is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    FunctionName = "${local.name_prefix}-${each.key}"
  }
  
  tags = merge(local.common_tags, {
    Function = each.key
    MetricType = "concurrent-executions"
  })
}

# ============================================================================
# API GATEWAY MONITORING
# ============================================================================

# API Gateway 4XX Errors Alarm
resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx" {
  count = var.api_gateway_id != "" ? 1 : 0
  
  alarm_name          = "${local.name_prefix}-api-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.api_gateway_4xx_threshold
  alarm_description   = "API Gateway 4XX error rate is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ApiId = var.api_gateway_id
  }
  
  tags = merge(local.common_tags, {
    Service = "api-gateway"
    MetricType = "4xx-errors"
  })
}

# API Gateway 5XX Errors Alarm
resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx" {
  count = var.api_gateway_id != "" ? 1 : 0
  
  alarm_name          = "${local.name_prefix}-api-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.api_gateway_5xx_threshold
  alarm_description   = "API Gateway 5XX error rate is too high"
  alarm_actions       = var.environment == "production" ? [aws_sns_topic.critical_alerts[0].arn] : [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ApiId = var.api_gateway_id
  }
  
  tags = merge(local.common_tags, {
    Service = "api-gateway"
    MetricType = "5xx-errors"
    Severity = "critical"
  })
}

# API Gateway Latency Alarm
resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  count = var.api_gateway_id != "" ? 1 : 0
  
  alarm_name          = "${local.name_prefix}-api-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Average"
  threshold           = var.api_gateway_latency_threshold_ms
  alarm_description   = "API Gateway latency is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ApiId = var.api_gateway_id
  }
  
  tags = merge(local.common_tags, {
    Service = "api-gateway"
    MetricType = "latency"
  })
}

# ============================================================================
# DYNAMODB MONITORING
# ============================================================================

# DynamoDB Throttled Requests Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  for_each = var.dynamodb_table_names
  
  alarm_name          = "${local.name_prefix}-${each.key}-dynamodb-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "DynamoDB table ${each.value} is being throttled"
  alarm_actions       = var.environment == "production" ? [aws_sns_topic.critical_alerts[0].arn] : [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    TableName = each.value
  }
  
  tags = merge(local.common_tags, {
    Table = each.key
    MetricType = "throttles"
    Severity = "critical"
  })
}

# DynamoDB Consumed Read Capacity Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_read_capacity" {
  for_each = var.dynamodb_table_names
  
  alarm_name          = "${local.name_prefix}-${each.key}-read-capacity"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ConsumedReadCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.dynamodb_read_capacity_threshold
  alarm_description   = "DynamoDB table ${each.value} read capacity consumption is high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    TableName = each.value
  }
  
  tags = merge(local.common_tags, {
    Table = each.key
    MetricType = "read-capacity"
  })
}

# DynamoDB Consumed Write Capacity Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_write_capacity" {
  for_each = var.dynamodb_table_names
  
  alarm_name          = "${local.name_prefix}-${each.key}-write-capacity"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ConsumedWriteCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.dynamodb_write_capacity_threshold
  alarm_description   = "DynamoDB table ${each.value} write capacity consumption is high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    TableName = each.value
  }
  
  tags = merge(local.common_tags, {
    Table = each.key
    MetricType = "write-capacity"
  })
}

# ============================================================================
# CUSTOM APPLICATION METRICS
# ============================================================================

# Custom business metrics alarms (if enabled)
resource "aws_cloudwatch_metric_alarm" "custom_trading_signals" {
  count = var.enable_business_metrics ? 1 : 0
  
  alarm_name          = "${local.name_prefix}-trading-signals-anomaly"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "TradingSignalsGenerated"
  namespace           = "TradePulse/Business"
  period              = "900"  # 15 minutes
  statistic           = "Sum"
  threshold           = var.trading_signals_min_threshold
  alarm_description   = "Trading signals generation has dropped significantly"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "breaching"
  
  tags = merge(local.common_tags, {
    MetricType = "business-metric"
    BusinessKPI = "trading-signals"
  })
}

# Custom error tracking
resource "aws_cloudwatch_metric_alarm" "custom_application_errors" {
  count = var.enable_business_metrics ? 1 : 0
  
  alarm_name          = "${local.name_prefix}-application-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApplicationErrors"
  namespace           = "TradePulse/Application"
  period              = "300"
  statistic           = "Sum"
  threshold           = var.application_error_threshold
  alarm_description   = "Application error count is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
  
  tags = merge(local.common_tags, {
    MetricType = "application-errors"
  })
}

# ============================================================================
# CLOUDWATCH DASHBOARDS
# ============================================================================

# Main monitoring dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name_prefix}-monitoring-dashboard"
  
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
            for func_name in keys(var.lambda_functions) : [
              "AWS/Lambda", "Duration", "FunctionName", "${local.name_prefix}-${func_name}"
            ]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Lambda Function Duration"
          period  = 300
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
            for func_name in keys(var.lambda_functions) : [
              "AWS/Lambda", "ErrorRate", "FunctionName", "${local.name_prefix}-${func_name}"
            ]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Lambda Function Error Rate"
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
          metrics = var.api_gateway_id != "" ? [
            ["AWS/ApiGateway", "4XXError", "ApiId", var.api_gateway_id],
            [".", "5XXError", ".", "."],
            [".", "Latency", ".", "."]
          ] : []
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "API Gateway Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            for table_name in values(var.dynamodb_table_names) : [
              "AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", table_name
            ]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "DynamoDB Read Capacity"
          period  = 300
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# Performance dashboard (if enabled)
resource "aws_cloudwatch_dashboard" "performance" {
  count = var.enable_performance_monitoring ? 1 : 0
  
  dashboard_name = "${local.name_prefix}-performance-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 24
        height = 6
        
        properties = {
          metrics = var.enable_business_metrics ? [
            ["TradePulse/Business", "TradingSignalsGenerated"],
            ["TradePulse/Application", "ApplicationErrors"]
          ] : []
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Business Metrics"
          period  = 300
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# ============================================================================
# DATA SOURCES
# ============================================================================

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}