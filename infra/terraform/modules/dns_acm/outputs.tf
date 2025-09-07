output "hosted_zone_id" {
  value = aws_route53_zone.root.zone_id
}

output "app_domain" {
  value = "${var.app_subdomain}.${var.root_domain}"
}

output "acm_cert_arn" {
  value = aws_acm_certificate_validation.cert.certificate_arn
}
