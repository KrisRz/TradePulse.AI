variable "app_name" {
  description = "Application name"
  type        = string
}

variable "env" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "websocket_api_id" {
  description = "WebSocket API Gateway ID for monitoring"
  type        = string
}

variable "ai_pipeline_arn" {
  description = "ARN of AI pipeline Step Function for monitoring"
  type        = string
}

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 500
}

variable "budget_alert_emails" {
  description = "List of email addresses for budget alerts"
  type        = list(string)
  default     = []
}

variable "alert_emails" {
  description = "List of email addresses for system alerts"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
