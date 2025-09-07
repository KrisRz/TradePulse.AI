# Local variables
locals {
  app_name = var.app_name
  env      = var.env

  common_tags = {
    Application = "TradePulse.AI"
    Environment = var.env
    ManagedBy   = "Terraform"
    Owner       = "TradePulse-Team"
    CostCenter  = var.env == "prod" ? "Production" : "Development"
  }
}

# DNS and SSL certificates
module "dns" {
  source        = "../../modules/dns_acm"
  providers     = { aws.us_east_1 = aws.us_east_1 }
  root_domain   = var.root_domain
  app_subdomain = var.app_subdomain
  tags          = local.common_tags
}

# Enhanced DynamoDB with multiple tables
module "database" {
  source                        = "../../modules/dynamodb"
  table_name                    = "${local.app_name}-${local.env}-table"
  app_name                      = local.app_name
  env                           = local.env
  enable_point_in_time_recovery = var.env == "prod" ? true : false
  tags                          = local.common_tags
}

# S3 buckets for models and layers
resource "aws_s3_bucket" "models" {
  bucket = "${local.app_name}-${local.env}-models"
  tags   = local.common_tags
}

resource "aws_s3_bucket" "lambda_layers" {
  bucket = "${local.app_name}-${local.env}-layers"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lambda layers for AI models
module "lambda_layers" {
  source        = "../../modules/lambda_layers"
  app_name      = local.app_name
  env           = local.env
  layers_bucket = aws_s3_bucket.lambda_layers.bucket
  model_version = var.model_version

  # For dev, we'll manually upload layers initially
  auto_upload_layers = false
}

# Enhanced API Gateway with layers support
module "api" {
  source        = "../../modules/api_lambda"
  function_name = "${local.app_name}-${local.env}-api"
  zip_path      = var.lambda_zip_path
  env           = local.env
  timeout       = 10
  memory_size   = 256 # Minimal memory for dev environment

  # Use API dependencies layer
  layers = [
    module.lambda_layers.api_dependencies_layer_arn,
    module.lambda_layers.binance_client_layer_arn
  ]

  environment = {
    TABLE_NAME              = module.database.table_name
    CONNECTIONS_TABLE_NAME  = module.database.connections_table_name
    MARKET_CACHE_TABLE_NAME = module.database.market_cache_table_name
    MODEL_BUCKET            = aws_s3_bucket.models.bucket
    BINANCE_API_KEY_PARAM   = "/tradepulse/${local.env}/BINANCE_API_KEY"
    BINANCE_SECRET_PARAM    = "/tradepulse/${local.env}/BINANCE_SECRET_KEY"
    JWT_SECRET_PARAM        = "/tradepulse/${local.env}/JWT_SECRET_KEY"
  }

  policy_json = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DeleteItem"
        ],
        Resource = [
          module.database.table_arn,
          module.database.connections_table_arn,
          module.database.market_cache_table_arn,
          "${module.database.table_arn}/*",
          "${module.database.connections_table_arn}/*",
          "${module.database.market_cache_table_arn}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ],
        Resource = "arn:aws:ssm:${var.region}:*:parameter/tradepulse/${local.env}/*"
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Resource = "${aws_s3_bucket.models.arn}/*"
      }
    ]
  })

  tags = local.common_tags
}

# Frontend hosting with enhanced configuration
module "frontend" {
  source            = "../../modules/frontend_static_site"
  bucket_name       = "${local.app_name}-${local.env}-site"
  create_cloudfront = var.create_cloudfront
  domain_name       = module.dns.app_domain
  acm_cert_arn      = module.dns.acm_cert_arn
  api_domain_name   = module.api.api_domain_name
  tags              = local.common_tags
}

# WebSocket API for real-time data (placeholder Lambda ARNs for now)
module "websocket_api" {
  source   = "../../modules/websocket_api"
  app_name = local.app_name
  env      = local.env

  # These will be actual Lambda ARNs when we create the Lambda functions
  websocket_authorizer_lambda_arn  = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-websocket-authorizer"
  websocket_authorizer_lambda_name = "${local.app_name}-${local.env}-websocket-authorizer"
  connection_handler_lambda_arn    = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-connection-handler"
  connection_handler_lambda_name   = "${local.app_name}-${local.env}-connection-handler"

  tags = local.common_tags
}

# Step Functions for AI processing (placeholder Lambda ARNs for now)
module "step_functions" {
  source   = "../../modules/step_functions"
  app_name = local.app_name
  env      = local.env

  # AI Pipeline Lambda ARNs (placeholders)
  feature_engineering_lambda_arn = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-feature-engineering"
  ai_inference_lambda_arn        = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-ai-inference"
  ensemble_aggregator_lambda_arn = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-ensemble-aggregator"
  risk_assessment_lambda_arn     = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-risk-assessment"
  signal_generator_lambda_arn    = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-signal-generator"

  # Model Retraining Lambda ARNs (placeholders)
  data_preparation_lambda_arn = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-data-preparation"
  model_training_lambda_arn   = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-model-training"
  model_validation_lambda_arn = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-model-validation"
  model_deployment_lambda_arn = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-model-deployment"

  # Emergency Lambda ARNs (placeholders)
  position_closer_lambda_arn = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-position-closer"
  notification_lambda_arn    = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-notification"
  audit_logger_lambda_arn    = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${local.app_name}-${local.env}-audit-logger"

  tags = local.common_tags
}

# EventBridge for event-driven architecture
module "eventbridge" {
  source   = "../../modules/eventbridge"
  app_name = local.app_name
  env      = local.env

  ai_pipeline_step_function_arn      = module.step_functions.ai_pipeline_arn
  emergency_halt_step_function_arn   = module.step_functions.emergency_halt_arn
  model_retraining_step_function_arn = module.step_functions.model_retraining_arn

  tags = local.common_tags
}

# Comprehensive monitoring
module "monitoring" {
  source   = "../../modules/monitoring"
  app_name = local.app_name
  env      = local.env

  # Resource ARNs for monitoring
  websocket_api_id     = module.websocket_api.websocket_api_id
  ai_pipeline_arn      = module.step_functions.ai_pipeline_arn
  monthly_budget_limit = var.env == "prod" ? 150 : 10 # $10 for dev, $150 for prod
  budget_alert_emails  = var.alert_emails
  alert_emails         = var.alert_emails

  tags = local.common_tags
}

# SSM Parameters for secrets (uncomment when ready to deploy)
module "secrets" {
  source      = "../../modules/ssm_params"
  path_prefix = "/tradepulse/${local.env}"
  secrets = {
    BINANCE_API_KEY    = var.binance_api_key != "" ? var.binance_api_key : "PLACEHOLDER"
    BINANCE_SECRET_KEY = var.binance_secret_key != "" ? var.binance_secret_key : "PLACEHOLDER"
    JWT_SECRET_KEY     = var.jwt_secret_key != "" ? var.jwt_secret_key : "PLACEHOLDER"
  }
  tags = local.common_tags
}

# Data sources
data "aws_caller_identity" "current" {}
