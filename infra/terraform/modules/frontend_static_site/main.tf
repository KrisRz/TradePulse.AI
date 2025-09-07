resource "aws_s3_bucket" "site" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_website_configuration" "site" {
  bucket = aws_s3_bucket.site.id
  index_document {
    suffix = "index.html"
  }
  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Opcjonalny CloudFront (zalecany dla HTTPS/domeny i cache)
resource "aws_cloudfront_origin_access_control" "oac" {
  count                             = var.create_cloudfront ? 1 : 0
  name                              = "${var.bucket_name}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Polityki cache i request (API: no-cache + forward wszystko co potrzeba)
resource "aws_cloudfront_cache_policy" "api" {
  count       = var.create_cloudfront && var.api_domain_name != null ? 1 : 0
  name        = "api-no-cache"
  default_ttl = 0
  max_ttl     = 0
  min_ttl     = 0
  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
    headers_config { header_behavior = "none" }
    cookies_config { cookie_behavior = "all" }
    query_strings_config { query_string_behavior = "all" }
  }
}

resource "aws_cloudfront_origin_request_policy" "api" {
  count = var.create_cloudfront && var.api_domain_name != null ? 1 : 0
  name  = "api-forward-all"
  cookies_config { cookie_behavior = "all" }
  headers_config { header_behavior = "allViewer" }
  query_strings_config { query_string_behavior = "all" }
}

resource "aws_cloudfront_distribution" "cdn" {
  count = var.create_cloudfront ? 1 : 0

  enabled             = true
  price_class         = "PriceClass_100"
  default_root_object = "index.html"

  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3Origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.oac[0].id
  }

  dynamic "origin" {
    for_each = var.api_domain_name == null ? [] : [var.api_domain_name]
    content {
      domain_name = origin.value
      origin_id   = "apiOrigin"
      custom_origin_config {
        origin_protocol_policy = "https-only"
        http_port              = 80
        https_port             = 443
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  default_cache_behavior {
    target_origin_id       = "s3Origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  dynamic "ordered_cache_behavior" {
    for_each = var.api_domain_name == null ? [] : [1]
    content {
      path_pattern             = "/api/*"
      target_origin_id         = "apiOrigin"
      viewer_protocol_policy   = "redirect-to-https"
      allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods           = ["GET", "HEAD", "OPTIONS"]
      compress                 = true
      cache_policy_id          = aws_cloudfront_cache_policy.api[0].id
      origin_request_policy_id = aws_cloudfront_origin_request_policy.api[0].id
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn            = var.acm_cert_arn != null ? var.acm_cert_arn : null
    ssl_support_method             = var.acm_cert_arn != null ? "sni-only" : null
    cloudfront_default_certificate = var.acm_cert_arn == null
  }
}

# Polityka bucketu, żeby CloudFront (OAC) mógł czytać
resource "aws_s3_bucket_policy" "allow_cf" {
  count  = var.create_cloudfront ? 1 : 0
  bucket = aws_s3_bucket.site.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid       = "AllowCloudFrontOAC",
      Effect    = "Allow",
      Principal = { Service = "cloudfront.amazonaws.com" },
      Action    = ["s3:GetObject"],
      Resource  = ["${aws_s3_bucket.site.arn}/*"],
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.cdn[0].arn
        }
      }
    }]
  })
}
