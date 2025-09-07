variable "app_name" {
  type = string
}

variable "lambda_zip_path" {
  type = string
}

variable "create_cloudfront" {
  type    = bool
  default = true
}

variable "root_domain" {
  type    = string
  default = "tradepulse.ai"
}

variable "app_subdomain" {
  type    = string
  default = "app"
}
