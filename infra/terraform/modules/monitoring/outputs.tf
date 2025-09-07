output "dashboard_url" {
  description = "URL of CloudWatch dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.trading_overview.dashboard_name}"
}

output "critical_alerts_topic_arn" {
  description = "ARN of critical alerts SNS topic"
  value       = aws_sns_topic.critical_alerts.arn
}

output "performance_alerts_topic_arn" {
  description = "ARN of performance alerts SNS topic"
  value       = aws_sns_topic.performance_alerts.arn
}

output "budget_name" {
  description = "Name of AWS budget"
  value       = aws_budgets_budget.monthly_cost.name
}

output "alarm_arns" {
  description = "Map of all CloudWatch alarm ARNs"
  value = {
    lambda_errors      = aws_cloudwatch_metric_alarm.lambda_errors.arn
    lambda_duration    = aws_cloudwatch_metric_alarm.lambda_duration.arn
    dynamodb_throttles = aws_cloudwatch_metric_alarm.dynamodb_throttles.arn
    websocket_errors   = aws_cloudwatch_metric_alarm.websocket_errors.arn
  }
}
