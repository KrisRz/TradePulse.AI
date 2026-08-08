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

resource "aws_lambda_function_url" "venue_status" {
  function_name      = aws_lambda_function.venue_status.function_name
  authorization_type = "NONE"
}

# `authorization_type = NONE` on the URL is not enough on its own — without
# this resource policy the URL answers 403, which CloudFront then swaps for the
# error page. The endpoint is read-only and public by design.
resource "aws_lambda_permission" "venue_status_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.venue_status.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

# Reaching the URL and invoking the function are two separate authorisations —
# since Oct 2025 a public URL needs both, and with only the one above it answers
# 403 no matter what. `infra-serverless/main.tf` had to add this out of band
# because AWS provider 5.x cannot express the condition; this root runs
# provider 6.x, where it is a first-class argument. The condition matters: it
# keeps the grant to invocations that arrive through the URL, not to
# lambda:Invoke generally.
resource "aws_lambda_permission" "venue_status_invoke" {
  statement_id             = "AllowPublicFunctionUrlInvoke"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.venue_status.function_name
  principal                = "*"
  invoked_via_function_url = true
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
