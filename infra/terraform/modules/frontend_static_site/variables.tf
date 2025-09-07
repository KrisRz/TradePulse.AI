variable "bucket_name" {
  type = string
}

variable "create_cloudfront" {
  type    = bool
  default = true
}

variable "domain_name" {
  type    = string
  default = null
}

variable "acm_cert_arn" {
  type    = string
  default = null
}

variable "api_domain_name" {
  type    = string
  default = null
}
