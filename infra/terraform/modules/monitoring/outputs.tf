# TradePulse.AI - Monitoring Module Outputs
# Professional output definitions for monitoring resources

# ============================================================================
# SNS TOPICS OUTPUTS
# ============================================================================

output "sns_alerts_topic_arn" {
  description = "ARN of the main alerts SNS topic"
  value       = aws_sns_topic.alerts.arn
}

output "sns_alerts_topic_name" {
  description = "Name of the main alerts SNS topic"
  value       = aws_sns_topic.alerts.name
}

output "sns_critical_alerts_topic_arn" {
  description = "ARN of the critical alerts SNS topic (production only)"
  value       = var.environment == "production" ? aws_sns_topic.critical_alerts[0].arn : ""
}

output "sns_performance_topic_arn" {
  description = "ARN of the performance monitoring SNS topic (if enabled)"
  value       = var.enable_performance_monitoring ? aws_sns_topic.performance[0].arn : ""
}

output "sns_topic_arns" {
  description = "Map of all SNS topic ARNs"
  value = {
    alerts           = aws_sns_topic.alerts.arn
    critical_alerts  = var.environment == "production" ? aws_sns_topic.critical_alerts[0].arn : ""
    performance      = var.enable_performance_monitoring ? aws_sns_topic.performance[0].arn : ""
  }
}

# ============================================================================
# CLOUDWATCH LOG GROUPS OUTPUTS
# ============================================================================

output "application_log_groups" {
  description = "Map of Lambda function log group names"
  value       = { for k, lg in aws_cloudwatch_log_group.application : k => lg.name }
}

output "application_log_group_arns" {
  description = "Map of Lambda function log group ARNs"
  value       = { for k, lg in aws_cloudwatch_log_group.application : k => lg.arn }
}

output "custom_metrics_log_group_name" {
  description = "Name of the custom metrics log group (if enabled)"
  value       = var.enable_custom_metrics ? aws_cloudwatch_log_group.custom_metrics[0].name : ""
}

output "custom_metrics_log_group_arn" {
  description = "ARN of the custom metrics log group (if enabled)"
  value       = var.enable_custom_metrics ? aws_cloudwatch_log_group.custom_metrics[0].arn : ""
}

# ============================================================================
# CLOUDWATCH ALARMS OUTPUTS
# ============================================================================

output "lambda_alarm_names" {
  description = "Map of Lambda function alarm names by type"
  value = {
    error_rate            = { for k, alarm in aws_cloudwatch_metric_alarm.lambda_error_rate : k => alarm.alarm_name }
    duration             = { for k, alarm in aws_cloudwatch_metric_alarm.lambda_duration : k => alarm.alarm_name }
    throttles            = { for k, alarm in aws_cloudwatch_metric_alarm.lambda_throttles : k => alarm.alarm_name }
    concurrent_executions = { for k, alarm in aws_cloudwatch_metric_alarm.lambda_concurrent_executions : k => alarm.alarm_name }
  }
}

output "lambda_alarm_arns" {
  description = "Map of Lambda function alarm ARNs by type"
  value = {
    error_rate            = { for k, alarm in aws_cloudwatch_metric_alarm.lambda_error_rate : k => alarm.arn }
    duration             = { for k, alarm in aws_cloudwatch_metric_alarm.lambda_duration : k => alarm.arn }
    throttles            = { for k, alarm in aws_cloudwatch_metric_alarm.lambda_throttles : k => alarm.arn }
    concurrent_executions = { for k, alarm in aws_cloudwatch_metric_alarm.lambda_concurrent_executions : k => alarm.arn }
  }
}

output "api_gateway_alarm_names" {
  description = "Map of API Gateway alarm names"
  value = var.api_gateway_id != "" ? {
    "4xx_errors" = aws_cloudwatch_metric_alarm.api_gateway_4xx[0].alarm_name
    "5xx_errors" = aws_cloudwatch_metric_alarm.api_gateway_5xx[0].alarm_name
    "latency"    = aws_cloudwatch_metric_alarm.api_gateway_latency[0].alarm_name
  } : {}
}

output "api_gateway_alarm_arns" {
  description = "Map of API Gateway alarm ARNs"
  value = var.api_gateway_id != "" ? {
    "4xx_errors" = aws_cloudwatch_metric_alarm.api_gateway_4xx[0].arn
    "5xx_errors" = aws_cloudwatch_metric_alarm.api_gateway_5xx[0].arn
    "latency"    = aws_cloudwatch_metric_alarm.api_gateway_latency[0].arn
  } : {}
}

output "dynamodb_alarm_names" {
  description = "Map of DynamoDB alarm names by type"
  value = {
    throttles      = { for k, alarm in aws_cloudwatch_metric_alarm.dynamodb_throttles : k => alarm.alarm_name }
    read_capacity  = { for k, alarm in aws_cloudwatch_metric_alarm.dynamodb_read_capacity : k => alarm.alarm_name }
    write_capacity = { for k, alarm in aws_cloudwatch_metric_alarm.dynamodb_write_capacity : k => alarm.alarm_name }
  }
}

output "dynamodb_alarm_arns" {
  description = "Map of DynamoDB alarm ARNs by type"
  value = {
    throttles      = { for k, alarm in aws_cloudwatch_metric_alarm.dynamodb_throttles : k => alarm.arn }
    read_capacity  = { for k, alarm in aws_cloudwatch_metric_alarm.dynamodb_read_capacity : k => alarm.arn }
    write_capacity = { for k, alarm in aws_cloudwatch_metric_alarm.dynamodb_write_capacity : k => alarm.arn }
  }
}

output "custom_business_alarm_names" {
  description = "Names of custom business metric alarms (if enabled)"
  value = var.enable_business_metrics ? {
    trading_signals     = aws_cloudwatch_metric_alarm.custom_trading_signals[0].alarm_name
    application_errors  = aws_cloudwatch_metric_alarm.custom_application_errors[0].alarm_name
  } : {}
}

output "custom_business_alarm_arns" {
  description = "ARNs of custom business metric alarms (if enabled)"
  value = var.enable_business_metrics ? {
    trading_signals     = aws_cloudwatch_metric_alarm.custom_trading_signals[0].arn
    application_errors  = aws_cloudwatch_metric_alarm.custom_application_errors[0].arn
  } : {}
}

# ============================================================================
# CLOUDWATCH DASHBOARDS OUTPUTS
# ============================================================================

output "main_dashboard_name" {
  description = "Name of the main monitoring dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "main_dashboard_url" {
  description = "URL to access the main monitoring dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "performance_dashboard_name" {
  description = "Name of the performance monitoring dashboard (if enabled)"
  value       = var.enable_performance_monitoring ? aws_cloudwatch_dashboard.performance[0].dashboard_name : ""
}

output "performance_dashboard_url" {
  description = "URL to access the performance monitoring dashboard (if enabled)"
  value       = var.enable_performance_monitoring ? "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.performance[0].dashboard_name}" : ""
}

output "dashboard_urls" {
  description = "Map of all dashboard URLs"
  value = {
    main        = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
    performance = var.enable_performance_monitoring ? "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.performance[0].dashboard_name}" : ""
  }
}

# ============================================================================
# MONITORING CONFIGURATION SUMMARY
# ============================================================================

output "monitoring_config_summary" {
  description = "Summary of monitoring configuration"
  value = {
    lambda_functions_monitored    = length(var.lambda_functions)
    api_gateway_monitoring       = var.api_gateway_id != ""
    dynamodb_tables_monitored    = length(var.dynamodb_table_names)
    
    alerting = {
      email_subscriptions         = length(var.alert_email_addresses)
      critical_email_subscriptions = length(var.critical_alert_email_addresses)
      slack_integration          = var.slack_webhook_url != ""
    }
    
    features = {
      performance_monitoring     = var.enable_performance_monitoring
      custom_metrics            = var.enable_custom_metrics
      business_metrics          = var.enable_business_metrics
      detailed_monitoring       = var.enable_detailed_monitoring
    }
    
    log_retention_days = var.log_retention_days
  }
}

# ============================================================================
# ALERT THRESHOLDS SUMMARY
# ============================================================================

output "alert_thresholds" {
  description = "Summary of configured alert thresholds"
  value = {
    lambda = {
      error_rate_percent           = var.lambda_error_rate_threshold
      duration_ms                 = var.lambda_duration_threshold_ms
      concurrent_executions       = var.lambda_concurrent_executions_threshold
    }
    
    api_gateway = var.api_gateway_id != "" ? {
      "4xx_errors"                = var.api_gateway_4xx_threshold
      "5xx_errors"                = var.api_gateway_5xx_threshold
      latency_ms                  = var.api_gateway_latency_threshold_ms
    } : {}
    
    dynamodb = {
      read_capacity_threshold     = var.dynamodb_read_capacity_threshold
      write_capacity_threshold    = var.dynamodb_write_capacity_threshold
    }
    
    business_metrics = var.enable_business_metrics ? {
      trading_signals_min         = var.trading_signals_min_threshold
      application_errors_max      = var.application_error_threshold
    } : {}
  }
}

# ============================================================================
# INTEGRATION OUTPUTS FOR OTHER MODULES
# ============================================================================

output "integration_info" {
  description = "Information for integration with other modules"
  value = {
    # For Lambda functions to publish custom metrics
    custom_metrics_log_group = var.enable_custom_metrics ? aws_cloudwatch_log_group.custom_metrics[0].name : ""
    
    # For SNS topic integration
    main_alerts_topic_arn    = aws_sns_topic.alerts.arn
    critical_alerts_topic_arn = var.environment == "production" ? aws_sns_topic.critical_alerts[0].arn : ""
    
    # For CloudWatch Logs integration
    lambda_log_groups        = { for k, lg in aws_cloudwatch_log_group.application : k => lg.name }
    
    # Monitoring endpoints
    dashboard_names = {
      main        = aws_cloudwatch_dashboard.main.dashboard_name
      performance = var.enable_performance_monitoring ? aws_cloudwatch_dashboard.performance[0].dashboard_name : ""
    }
  }
}

# ============================================================================
# COST INFORMATION
# ============================================================================

output "cost_factors" {
  description = "Monitoring-related cost factors"
  value = {
    cloudwatch_alarms_count      = (
      length(var.lambda_functions) * 4 +  # 4 alarms per Lambda function
      (var.api_gateway_id != "" ? 3 : 0) +  # 3 API Gateway alarms
      length(var.dynamodb_table_names) * 3 +  # 3 alarms per DynamoDB table
      (var.enable_business_metrics ? 2 : 0)  # 2 custom business alarms
    )
    
    sns_topics_count            = 1 + (var.environment == "production" ? 1 : 0) + (var.enable_performance_monitoring ? 1 : 0)
    sns_subscriptions_count     = length(var.alert_email_addresses) + length(var.critical_alert_email_addresses) + (var.slack_webhook_url != "" ? 1 : 0)
    
    cloudwatch_logs_groups      = length(var.lambda_functions) + (var.enable_custom_metrics ? 1 : 0)
    cloudwatch_dashboards       = 1 + (var.enable_performance_monitoring ? 1 : 0)
    
    detailed_monitoring_enabled = var.enable_detailed_monitoring
    
    estimated_monthly_costs = {
      cloudwatch_alarms      = (length(var.lambda_functions) * 4 + (var.api_gateway_id != "" ? 3 : 0) + length(var.dynamodb_table_names) * 3 + (var.enable_business_metrics ? 2 : 0)) * 0.10
      sns_notifications      = (length(var.alert_email_addresses) + length(var.critical_alert_email_addresses)) * 0.50  # ~$0.50/month per email endpoint
      cloudwatch_dashboards = (1 + (var.enable_performance_monitoring ? 1 : 0)) * 3.00  # ~$3.00/month per dashboard
      log_storage_gb         = "variable_based_on_usage"
      detailed_monitoring    = var.enable_detailed_monitoring ? "additional_cost_per_metric" : 0
    }
  }
}

# ============================================================================
# TROUBLESHOOTING OUTPUTS
# ============================================================================

output "troubleshooting_info" {
  description = "Information for troubleshooting monitoring setup"
  value = {
    sns_topic_policy_check = "Ensure proper IAM permissions for SNS topic publishing"
    
    email_confirmation_required = length(var.alert_email_addresses) > 0 ? "Email subscriptions require manual confirmation" : "no_email_subscriptions"
    
    custom_metrics_namespace = {
      business_metrics    = "TradePulse/Business"
      application_metrics = "TradePulse/Application"
    }
    
    log_group_retention = "${var.log_retention_days} days"
    
    dashboard_access = {
      main_dashboard        = aws_cloudwatch_dashboard.main.dashboard_name
      performance_dashboard = var.enable_performance_monitoring ? aws_cloudwatch_dashboard.performance[0].dashboard_name : "not_enabled"
    }
    
    alarm_state_reasons = "Check individual alarm descriptions for threshold details"
    
    integration_points = {
      lambda_functions   = "Ensure Lambda functions have CloudWatch Logs permissions"
      api_gateway       = "Ensure API Gateway has CloudWatch metrics enabled"
      dynamodb_tables   = "Ensure DynamoDB tables have CloudWatch metrics enabled"
      custom_metrics    = "Use AWS SDK PutMetricData API to publish custom metrics"
    }
  }
}