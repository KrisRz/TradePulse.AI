output "trading_bus_arn" {
  description = "ARN of trading events EventBridge bus"
  value       = aws_cloudwatch_event_bus.trading.arn
}

output "trading_bus_name" {
  description = "Name of trading events EventBridge bus"
  value       = aws_cloudwatch_event_bus.trading.name
}

output "trading_events_queue_arn" {
  description = "ARN of trading events SQS queue"
  value       = aws_sqs_queue.trading_events.arn
}

output "trading_events_dlq_arn" {
  description = "ARN of trading events dead letter queue"
  value       = aws_sqs_queue.trading_events_dlq.arn
}

output "eventbridge_role_arn" {
  description = "ARN of EventBridge execution role"
  value       = aws_iam_role.eventbridge.arn
}

output "event_rule_arns" {
  description = "Map of all event rule ARNs"
  value = {
    market_data_updated      = aws_cloudwatch_event_rule.market_data_updated.arn
    trading_signal_generated = aws_cloudwatch_event_rule.trading_signal_generated.arn
    emergency_events         = aws_cloudwatch_event_rule.emergency_events.arn
    daily_retraining         = aws_cloudwatch_event_rule.daily_retraining.arn
  }
}
