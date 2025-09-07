output "api_url" {
  value = module.api.api_endpoint
}

output "bucket_name" {
  value = module.frontend.bucket_name
}

output "cloudfront_url" {
  value = module.frontend.cf_domain_name
}

output "app_domain" {
  value = module.dns.app_domain
}
