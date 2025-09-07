variable "app_name" {
  description = "Application name"
  type        = string
  default     = "tradepulse"
}

# env and region variables are defined in providers.tf

variable "lambda_zip_path" {
  description = "Path to Lambda deployment ZIP file"
  type        = string
  default     = "../../backend/dist/backend.zip"
}

variable "create_cloudfront" {
  description = "Whether to create CloudFront distribution"
  type        = bool
  default     = true
}

variable "root_domain" {
  description = "Root domain name"
  type        = string
  default     = "tradepulse.ai"
}

variable "app_subdomain" {
  description = "Application subdomain"
  type        = string
  default     = "dev"
}

variable "model_version" {
  description = "Version of trading models"
  type        = string
  default     = "v1.0.0"
}

# Alert configuration
variable "alert_emails" {
  description = "List of email addresses for alerts"
  type        = list(string)
  default     = []
}

# Secret variables (will be provided via terraform.tfvars or environment)
variable "binance_api_key" {
  description = "Binance API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "binance_secret_key" {
  description = "Binance secret key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT secret key"
  type        = string
  default     = ""
  sensitive   = true
}
