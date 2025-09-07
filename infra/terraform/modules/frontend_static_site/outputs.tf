output "bucket_name" {
  value = aws_s3_bucket.site.bucket
}

output "website_endpoint" {
  value = aws_s3_bucket_website_configuration.site.website_endpoint
}

output "cf_domain_name" {
  value = try(aws_cloudfront_distribution.cdn[0].domain_name, null)
}

output "cf_id" {
  value = try(aws_cloudfront_distribution.cdn[0].id, null)
}
