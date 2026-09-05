# Read-only status API for the site, served from the SAME origin as the page
# (`/api/*`) so it needs no CORS and no extra `connect-src` in the CSP.
#
# This function is new and lives in the unfrozen root: it adds a reader to the
# DynamoDB table and changes nothing about the M5 bots. Its IAM policy is
# GetItem/Query on that one table and nothing else.

data "archive_file" "venue_status" {
  type        = "zip"
  source_file = "${path.module}/lambda/venue_status.py"
  output_path = "${path.module}/.build/venue_status.zip"
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "venue_status" {
  name               = "tradepulse-site-status-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "venue_status" {
  statement {
    sid       = "ReadBotTable"
    actions   = ["dynamodb:GetItem", "dynamodb:Query"]
    resources = ["arn:aws:dynamodb:eu-west-2:590183672693:table/tradepulse_paper_bot"]
  }

  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.venue_status.arn}:*"]
  }
}

resource "aws_iam_role_policy" "venue_status" {
  name   = "tradepulse-site-status-policy"
  role   = aws_iam_role.venue_status.id
  policy = data.aws_iam_policy_document.venue_status.json
}

# Short retention: this logs one line per invocation and log ingestion is the
# only line item here that can grow with traffic.
resource "aws_cloudwatch_log_group" "venue_status" {
  name              = "/aws/lambda/tradepulse-site-status"
  retention_in_days = 7
}

resource "aws_lambda_function" "venue_status" {
  function_name    = "tradepulse-site-status"
  role             = aws_iam_role.venue_status.arn
  runtime          = "python3.11"
  handler          = "venue_status.handler"
  filename         = data.archive_file.venue_status.output_path
  source_code_hash = data.archive_file.venue_status.output_base64sha256
  timeout          = 10
  memory_size      = 256
  architectures    = ["x86_64"]

  environment {
    variables = {
      TABLE_NAME = "tradepulse_paper_bot"
    }
  }

  depends_on = [aws_cloudwatch_log_group.venue_status]
}

# The URL requires a signature, and only CloudFront has one (audit E2E
# 2026-09-04, E2). Before this it was `NONE` and answered 200 to anyone who knew
# the address, which meant the 30s edge cache bounded origin cost only for
# traffic that bothered to go through the edge. Low severity — it is a read-only
# status endpoint on a bot whose entire bill is $1.35/month — but "the cache
# protects the origin" was simply not true, and an unauthenticated Lambda URL is
# not the shape to carry into M6.
resource "aws_lambda_function_url" "venue_status" {
  function_name      = aws_lambda_function.venue_status.function_name
  authorization_type = "AWS_IAM"
}

# Reaching the URL and invoking the function are two separate authorisations —
# since Oct 2025 a URL needs both, and with only one of them it answers 403 no
# matter what. Both are now scoped to this distribution rather than to `*`:
# principal + `source_arn` together mean no other CloudFront distribution, in
# this account or anyone else's, can use them.
resource "aws_lambda_permission" "venue_status_url" {
  statement_id           = "AllowCloudFrontFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.venue_status.function_name
  principal              = "cloudfront.amazonaws.com"
  source_arn             = aws_cloudfront_distribution.site.arn
  function_url_auth_type = "AWS_IAM"
}

# `invoked_via_function_url` keeps the grant to invocations arriving through the
# URL, not to `lambda:Invoke` generally. AWS provider 6.x expresses it as a
# first-class argument; `infra-serverless/main.tf` had to do it out of band.
resource "aws_lambda_permission" "venue_status_invoke" {
  statement_id             = "AllowCloudFrontFunctionUrlInvoke"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.venue_status.function_name
  principal                = "cloudfront.amazonaws.com"
  source_arn               = aws_cloudfront_distribution.site.arn
  invoked_via_function_url = true
}

# Signs every origin request with SigV4 so the Lambda URL can tell CloudFront
# from the world. `always` is deliberate: it overwrites any Authorization header
# the viewer sent, which is what stops a caller from confusing the signature by
# supplying one of their own.
resource "aws_cloudfront_origin_access_control" "api" {
  name                              = "tradepulse-site-api"
  description                       = "SigV4 signing for the read-only state API origin"
  origin_access_control_origin_type = "lambda"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

locals {
  status_lambda_host = replace(
    replace(aws_lambda_function_url.venue_status.function_url, "https://", ""), "/", ""
  )
}

# 60s at the edge: the 4h bot writes at most once every four hours, so this
# bounds origin calls to ~1/min no matter how much traffic the page gets.
resource "aws_cloudfront_cache_policy" "api_short" {
  name        = "tradepulse-site-api-short"
  default_ttl = 60
  max_ttl     = 120
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "none"
    }
    enable_accept_encoding_gzip   = true
    enable_accept_encoding_brotli = true
  }
}

# Lambda function URLs reject a Host header that isn't their own.
data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}
