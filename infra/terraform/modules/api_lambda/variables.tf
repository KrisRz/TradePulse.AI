variable "function_name" {
  description = "Lambda function name"
  type        = string
}

variable "zip_path" {
  description = "Path to the Lambda deployment ZIP file"
  type        = string
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.11"
}

variable "handler" {
  description = "Lambda handler"
  type        = string
  default     = "main.lambda_handler"
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 1024
}

variable "layers" {
  description = "List of Lambda layer ARNs"
  type        = list(string)
  default     = []
}

variable "environment" {
  description = "Environment variables for Lambda"
  type        = map(string)
  default     = {}
}

variable "env" {
  description = "Environment name (dev/prod)"
  type        = string
}

variable "log_level" {
  description = "Log level for Lambda function"
  type        = string
  default     = "INFO"
}

variable "policy_json" {
  description = "Additional IAM policy JSON for Lambda execution role"
  type        = string
  default     = null
}

variable "dead_letter_queue_arn" {
  description = "ARN of SQS queue for dead letter queue"
  type        = string
  default     = null
}

variable "vpc_config" {
  description = "VPC configuration for Lambda"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "reserved_concurrency" {
  description = "Reserved concurrency for Lambda function"
  type        = number
  default     = null
}

variable "cors_configuration" {
  description = "CORS configuration for API Gateway"
  type = object({
    allow_credentials = bool
    allow_headers     = list(string)
    allow_methods     = list(string)
    allow_origins     = list(string)
    expose_headers    = list(string)
    max_age           = number
  })
  default = {
    allow_credentials = true
    allow_headers     = ["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins     = ["*"]
    expose_headers    = []
    max_age           = 86400
  }
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
