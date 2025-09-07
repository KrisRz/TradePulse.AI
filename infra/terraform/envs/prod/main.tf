module "dns" {
  source        = "../../modules/dns_acm"
  providers     = { aws.us_east_1 = aws.us_east_1 }
  root_domain   = var.root_domain
  app_subdomain = var.app_subdomain
}

module "db" {
  source     = "../../modules/dynamodb"
  table_name = "${var.app_name}-${var.env}-table"
}

module "api" {
  source        = "../../modules/api_lambda"
  function_name = "${var.app_name}-${var.env}-api"
  zip_path      = var.lambda_zip_path
  environment = {
    TABLE_NAME = module.db.table_name
  }
  policy_json = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect   = "Allow",
      Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"],
      Resource = module.db.table_arn
      }, {
      Effect   = "Allow",
      Action   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
      Resource = "arn:aws:ssm:${var.region}:*:parameter/tradepulse/${var.env}/*"
    }]
  })
}

module "frontend" {
  source            = "../../modules/frontend_static_site"
  bucket_name       = "${var.app_name}-${var.env}-site"
  create_cloudfront = var.create_cloudfront
  domain_name       = module.dns.app_domain
  acm_cert_arn      = module.dns.acm_cert_arn
  api_domain_name   = module.api.api_domain_name
}

# (opcjonalnie) sekrety SSM — można wdrożyć ręcznie w konsoli, ale moduł jest gotowy
# module "secrets" {
#   source      = "../../modules/ssm_params"
#   path_prefix = "/tradepulse/${var.env}"
#   secrets = {
#     BINANCE_API_KEY   = "***"
#     BINANCE_SECRET_KEY= "***"
#     JWT_SECRET_KEY    = "***"
#   }
# }
