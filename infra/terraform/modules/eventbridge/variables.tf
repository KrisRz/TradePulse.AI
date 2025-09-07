variable "app_name" {
  description = "Application name"
  type        = string
}

variable "env" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "ai_pipeline_step_function_arn" {
  description = "ARN of AI pipeline Step Function"
  type        = string
}

variable "emergency_halt_step_function_arn" {
  description = "ARN of emergency halt Step Function"
  type        = string
}

variable "model_retraining_step_function_arn" {
  description = "ARN of model retraining Step Function"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
