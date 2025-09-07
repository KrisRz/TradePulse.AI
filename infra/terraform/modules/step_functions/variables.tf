variable "app_name" {
  description = "Application name"
  type        = string
}

variable "env" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

# AI Pipeline Lambda ARNs
variable "feature_engineering_lambda_arn" {
  description = "ARN of feature engineering Lambda function"
  type        = string
}

variable "ai_inference_lambda_arn" {
  description = "ARN of AI inference Lambda function"
  type        = string
}

variable "ensemble_aggregator_lambda_arn" {
  description = "ARN of ensemble aggregator Lambda function"
  type        = string
}

variable "risk_assessment_lambda_arn" {
  description = "ARN of risk assessment Lambda function"
  type        = string
}

variable "signal_generator_lambda_arn" {
  description = "ARN of signal generator Lambda function"
  type        = string
}

# Model Retraining Lambda ARNs
variable "data_preparation_lambda_arn" {
  description = "ARN of data preparation Lambda function"
  type        = string
}

variable "model_training_lambda_arn" {
  description = "ARN of model training Lambda function"
  type        = string
}

variable "model_validation_lambda_arn" {
  description = "ARN of model validation Lambda function"
  type        = string
}

variable "model_deployment_lambda_arn" {
  description = "ARN of model deployment Lambda function"
  type        = string
}

# Emergency Functions Lambda ARNs
variable "position_closer_lambda_arn" {
  description = "ARN of position closer Lambda function"
  type        = string
}

variable "notification_lambda_arn" {
  description = "ARN of notification Lambda function"
  type        = string
}

variable "audit_logger_lambda_arn" {
  description = "ARN of audit logger Lambda function"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
