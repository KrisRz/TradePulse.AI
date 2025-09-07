output "ai_pipeline_arn" {
  description = "ARN of AI pipeline Step Function"
  value       = aws_sfn_state_machine.ai_pipeline.arn
}

output "ai_pipeline_name" {
  description = "Name of AI pipeline Step Function"
  value       = aws_sfn_state_machine.ai_pipeline.name
}

output "model_retraining_arn" {
  description = "ARN of model retraining Step Function"
  value       = aws_sfn_state_machine.model_retraining.arn
}

output "model_retraining_name" {
  description = "Name of model retraining Step Function"
  value       = aws_sfn_state_machine.model_retraining.name
}

output "emergency_halt_arn" {
  description = "ARN of emergency halt Step Function"
  value       = aws_sfn_state_machine.emergency_halt.arn
}

output "emergency_halt_name" {
  description = "Name of emergency halt Step Function"
  value       = aws_sfn_state_machine.emergency_halt.name
}

output "step_functions_role_arn" {
  description = "ARN of Step Functions execution role"
  value       = aws_iam_role.step_functions.arn
}

output "all_step_function_arns" {
  description = "Map of all Step Function ARNs"
  value = {
    ai_pipeline      = aws_sfn_state_machine.ai_pipeline.arn
    model_retraining = aws_sfn_state_machine.model_retraining.arn
    emergency_halt   = aws_sfn_state_machine.emergency_halt.arn
  }
}
