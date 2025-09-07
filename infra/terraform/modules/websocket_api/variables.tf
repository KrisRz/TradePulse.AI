variable "app_name" {
  description = "Application name"
  type        = string
}

variable "env" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "websocket_authorizer_lambda_arn" {
  description = "ARN of WebSocket authorizer Lambda function"
  type        = string
}

variable "websocket_authorizer_lambda_name" {
  description = "Name of WebSocket authorizer Lambda function"
  type        = string
}

variable "connection_handler_lambda_arn" {
  description = "ARN of WebSocket connection handler Lambda function"
  type        = string
}

variable "connection_handler_lambda_name" {
  description = "Name of WebSocket connection handler Lambda function"
  type        = string
}

variable "throttling_rate_limit" {
  description = "API Gateway throttling rate limit (requests per second)"
  type        = number
  default     = 1000
}

variable "throttling_burst_limit" {
  description = "API Gateway throttling burst limit"
  type        = number
  default     = 2000
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
