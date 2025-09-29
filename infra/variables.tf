variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "tradepulse"
}

variable "binance_api_key" {
  description = "Binance API Key"
  type        = string
  sensitive   = true
}

variable "binance_api_secret" {
  description = "Binance API Secret"
  type        = string
  sensitive   = true
}

variable "app_runner_cpu" {
  description = "App Runner CPU units (1024 = 1 vCPU)"
  type        = string
  default     = "1024"
}

variable "app_runner_memory" {
  description = "App Runner memory in MB"
  type        = string
  default     = "2048"
}

variable "app_runner_min_size" {
  description = "App Runner minimum instances"
  type        = number
  default     = 1
}

variable "app_runner_max_size" {
  description = "App Runner maximum instances"
  type        = number
  default     = 3
}

variable "enable_vpc" {
  description = "Enable VPC for private networking (adds ~$45/month NAT Gateway cost)"
  type        = bool
  default     = false # Disabled by default for cost optimization
}

variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring"
  type        = bool
  default     = true
}

# Domain configuration (Route 53)
variable "domain_name" {
  description = "Root domain managed in Route 53 (e.g., tradepulseai.co.uk)"
  type        = string
  default     = "tradepulseai.co.uk"
}

variable "apex_subdomain" {
  description = "Subdomain for backend (e.g., api). Leave empty to use root."
  type        = string
  default     = "api"
}

variable "frontend_subdomain" {
  description = "Subdomain for frontend app (e.g., app)"
  type        = string
  default     = "app"
}

variable "github_repo" {
  description = "GitHub repository for OIDC trust (format: org/repo)"
  type        = string
  default     = "KrisRz/TradePulse.AI"
}

variable "github_branch" {
  description = "GitHub branch for OIDC trust"
  type        = string
  default     = "main"
}

# Optional: Custom domain
variable "custom_domain" {
  description = "Custom domain for the application"
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for custom domain"
  type        = string
  default     = ""
}
