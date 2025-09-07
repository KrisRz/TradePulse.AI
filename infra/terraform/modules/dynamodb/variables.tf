variable "table_name" {
  description = "Main DynamoDB table name"
  type        = string
}

variable "app_name" {
  description = "Application name for resource naming"
  type        = string
}

variable "env" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery for the table"
  type        = bool
  default     = false
}

# KMS encryption uses default AWS managed key

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
