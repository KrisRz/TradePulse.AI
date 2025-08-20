# TradePulse.AI - Production Environment Infrastructure
# Professional AWS deployment with enterprise-grade architecture

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  
  # Remote state management
  backend "s3" {
    bucket         = "tradepulse-terraform-state-prod"
    key            = "production/terraform.tfstate"
    region         = "eu-west-2"
    encrypt        = true
    dynamodb_table = "tradepulse-terraform-locks"
  }
}

# Configure AWS Provider with default tags
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project           = "TradePulse.AI"
      Environment       = "production"
      ManagedBy         = "Terraform"
      Owner            = "TradePulse-AI-Team"
      CostCenter       = "trading-platform"
      DataClassification = "confidential"
      BackupRequired   = "true"
      MonitoringLevel  = "comprehensive"
      ComplianceLevel  = "high"
    }
  }
}

# Aliased provider for us-east-1 (CloudFront ACM, optional replication)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# Random suffix for unique resource names
resource "random_id" "deployment" {
  byte_length = 4
}

locals {
  deployment_id = random_id.deployment.hex
  common_tags = {
    DeploymentId = local.deployment_id
    CreatedBy    = "terraform"
    CreatedAt    = timestamp()
  }
  # Effective network IDs when adopting existing VPC
  effective_private_subnet_ids = var.vpc_adoption == "existing" && length(var.private_subnet_ids) > 0 ? var.private_subnet_ids : module.networking.private_subnet_ids
  effective_lambda_sg_id       = var.vpc_adoption == "existing" && var.lambda_security_group_id != "" ? var.lambda_security_group_id : module.security.lambda_security_group_id
}

# Core Infrastructure Modules
module "networking" {
  source = "../../modules/networking"
  
  environment    = var.environment
  deployment_id  = local.deployment_id
  aws_region     = var.aws_region
  
  # VPC Configuration
  vpc_cidr           = var.vpc_cidr
  availability_zones = data.aws_availability_zones.available.names
  
  # Security
  allowed_cidr_blocks = var.allowed_cidr_blocks
  enable_vpc_flow_logs = var.enable_vpc_flow_logs
  
  tags = local.common_tags
  
  # If adopting existing VPC, bypass creation and expose provided IDs
  providers = {
    aws = aws
  }
}

module "security" {
  source = "../../modules/security"
  
  environment   = var.environment
  deployment_id = local.deployment_id
  project_name  = var.project_name
  
  # API Security
  enable_waf           = var.enable_waf
  rate_limit_per_ip    = var.api_rate_limit
  allowed_cidr_blocks  = var.allowed_cidr_blocks
  
  # Secrets Management
  # Managed externally (pre-existing secret): tradepulse/trading-secrets-production
  secrets_config = {}
  
  # Certificate Management
  domain_name = var.domain_name
  
  tags = local.common_tags

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }
}

module "storage" {
  source = "../../modules/storage"
  
  environment   = var.environment
  deployment_id = local.deployment_id
  project_name  = var.project_name
  
  # DynamoDB Configuration
  tables_config = {
    # User and Authentication
    users = {
      hash_key           = "user_id"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = true
      enable_pitr        = true
      enable_streams     = false
      global_tables      = var.enable_global_tables
    }
    
    # Trading Data
    positions = {
      hash_key           = "position_id"
      range_key          = "timestamp"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = true
      enable_pitr        = true
      enable_streams     = true
      ttl_attribute      = "expires_at"
      global_tables      = var.enable_global_tables
    }
    
    signals = {
      hash_key           = "signal_id"
      range_key          = "created_at"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = true
      enable_pitr        = true
      enable_streams     = true
      ttl_attribute      = "expires_at"
      global_tables      = var.enable_global_tables
    }
    
    # Market Data
    live_candles = {
      hash_key           = "symbol_interval"
      range_key          = "timestamp"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = true
      enable_pitr        = false
      enable_streams     = true
      ttl_attribute      = "expires_at"
      global_tables      = false
    }
    
    # Portfolio Management
    virtual_portfolios = {
      hash_key           = "portfolio_id"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = true
      enable_pitr        = true
      enable_streams     = true
      global_tables      = var.enable_global_tables
    }
    
    virtual_transactions = {
      hash_key           = "transaction_id"
      range_key          = "timestamp"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = true
      enable_pitr        = true
      enable_streams     = false
      global_tables      = var.enable_global_tables
    }
    
    # ML Models and Performance
    model_performance = {
      hash_key           = "model_id"
      range_key          = "timestamp"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = true
      enable_pitr        = true
      enable_streams     = true
      global_tables      = var.enable_global_tables
    }
    
    # System Configuration
    system_config = {
      hash_key           = "config_key"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = true
      enable_pitr        = true
      enable_streams     = false
      global_tables      = var.enable_global_tables
    }
  }
  
  # S3 Configuration
  s3_buckets = {
    frontend = {
      purpose           = "static-website"
      enable_versioning = true
      enable_encryption = true
      enable_cors       = true
      lifecycle_rules   = var.s3_lifecycle_rules
    }
    
    data = {
      purpose           = "data-storage"
      enable_versioning = true
      enable_encryption = true
      enable_cors       = false
      lifecycle_rules   = var.s3_lifecycle_rules
    }
    
    models = {
      purpose           = "ml-models"
      enable_versioning = true
      enable_encryption = true
      enable_cors       = false
      lifecycle_rules   = var.s3_lifecycle_rules
    }
    
    backups = {
      purpose           = "system-backups"
      enable_versioning = true
      enable_encryption = true
      enable_cors       = false
      lifecycle_rules   = var.s3_lifecycle_rules
    }
  }
  
  # CloudFront distribution ARN for bucket policy binding
  cloudfront_distribution_arn = "arn:aws:cloudfront::590183672693:distribution/E2T06EN7O486LG"
  
  # Adopt existing resource names
  explicit_bucket_names = {
    frontend = "tradepulse-frontend-production-f3574173"
    models   = "tradepulse-ml-models-production-f3574173"
  }
  
  explicit_table_names = {
    users               = "tradepulse-users-production"
    positions           = "tradepulse-positions-production"
    signals             = "tradepulse-trading_signals-production"
    live_candles        = "tradepulse-live_candles-production"
    virtual_portfolios  = "tradepulse-virtual_portfolios-production"
    virtual_transactions = "tradepulse-virtual_transactions-production"
    model_performance   = "tradepulse-model_performance_metrics-production"
  }
  
  # Backup Configuration
  backup_retention_days         = var.backup_retention_days
  enable_cross_region_backup    = var.enable_cross_region_backup
  enable_point_in_time_recovery = var.enable_point_in_time_recovery
  
  tags = local.common_tags

  providers = {
    aws         = aws
    aws.replica = aws.us_east_1
  }
}

module "compute" {
  source = "../../modules/compute"
  
  environment   = var.environment
  deployment_id = local.deployment_id
  project_name  = var.project_name
  
  # Lambda Configuration
  lambda_functions = {
    backend_api = {
      filename         = "../../../app/backend/backend-lambda.zip"
      handler          = "lambda_handler.handler"
      runtime          = "python3.11"
      memory_size      = var.lambda_memory_size
      timeout          = var.lambda_timeout
      environment_vars = local.lambda_environment
      vpc_config = var.enable_vpc ? {
        subnet_ids         = local.effective_private_subnet_ids
        security_group_ids = [local.effective_lambda_sg_id]
      } : null
    }
    
    ai_signals = {
      filename         = "../../../app/backend/ai-signals-lambda.zip"
      handler          = "ai_handler.handler"
      runtime          = "python3.11"
      memory_size      = var.ai_lambda_memory_size
      timeout          = var.lambda_timeout
      environment_vars = local.lambda_environment
      vpc_config = var.enable_vpc ? {
        subnet_ids         = local.effective_private_subnet_ids
        security_group_ids = [local.effective_lambda_sg_id]
      } : null
    }
    
    data_collector = {
      filename         = "../../../app/backend/data-collector-lambda.zip"
      handler          = "data_collector.handler"
      runtime          = "python3.11"
      memory_size      = var.lambda_memory_size
      timeout          = 300
      environment_vars = local.lambda_environment
      vpc_config = var.enable_vpc ? {
        subnet_ids         = local.effective_private_subnet_ids
        security_group_ids = [local.effective_lambda_sg_id]
      } : null
    }
    
    position_monitor = {
      filename         = "../../../app/backend/position-monitor-lambda.zip"
      handler          = "position_monitor.handler"
      runtime          = "python3.11"
      memory_size      = var.lambda_memory_size
      timeout          = var.lambda_timeout
      environment_vars = local.lambda_environment
      vpc_config = var.enable_vpc ? {
        subnet_ids         = local.effective_private_subnet_ids
        security_group_ids = [local.effective_lambda_sg_id]
      } : null
    }
    
    health_monitor = {
      filename         = "../../../app/backend/health-monitor-lambda.zip"
      handler          = "health_monitor.handler"
      runtime          = "python3.11"
      memory_size      = 512
      timeout          = 60
      environment_vars = local.lambda_environment
      vpc_config = var.enable_vpc ? {
        subnet_ids         = local.effective_private_subnet_ids
        security_group_ids = [local.effective_lambda_sg_id]
      } : null
    }
    
    ml_model_updater = {
      filename         = "../../../app/backend/ml-model-updater-lambda.zip"
      handler          = "ml_model_updater.handler"
      runtime          = "python3.11"
      memory_size      = var.ml_lambda_memory_size
      timeout          = 900
      environment_vars = local.lambda_environment
      vpc_config = var.enable_vpc ? {
        subnet_ids         = module.networking.private_subnet_ids
        security_group_ids = [module.security.lambda_security_group_id]
      } : null
    }
  }
  
  # Adopt existing Lambda function names
  explicit_function_names = {
    backend_api      = "tradepulse-backend-api-production"
    ai_signals       = "tradepulse-ai-signals-production"
    data_collector   = "tradepulse-data-collector-production"
    position_monitor = "tradepulse-position-monitor-production"
    health_monitor   = "tradepulse-health-monitor-production"
    ml_model_updater = "tradepulse-ml-model-updater-production"
  }
  
  # API Gateway Configuration
  api_gateway_config = {
    name               = "${var.project_name}-api-${local.deployment_id}"
    description        = "TradePulse.AI Production API"
    protocol_type      = "HTTP"
    cors_enabled       = true
    throttle_burst     = var.api_throttle_burst
    throttle_rate      = var.api_throttle_rate
    custom_domain      = var.domain_name != "" ? var.domain_name : null
    certificate_arn    = var.domain_name != "" ? module.security.certificate_arn : null
  }
  
  # EventBridge Configuration
  eventbridge_rules = var.eventbridge_schedules
  
  # CloudFront Distribution
  cloudfront_config = {
    frontend_bucket_id     = module.storage.s3_bucket_ids["frontend"]
    frontend_bucket_domain = module.storage.s3_bucket_domains["frontend"]
    api_domain            = module.compute.api_gateway_domain
    price_class           = var.cloudfront_price_class
    custom_domain         = var.domain_name
    certificate_arn       = var.domain_name != "" ? module.security.certificate_arn : null
  }
  
  # Dependencies
  vpc_id                    = var.vpc_adoption == "existing" && var.vpc_id != "" ? var.vpc_id : module.networking.vpc_id
  public_subnet_ids         = module.networking.public_subnet_ids
  private_subnet_ids        = var.vpc_adoption == "existing" && length(var.private_subnet_ids) > 0 ? var.private_subnet_ids : module.networking.private_subnet_ids
  lambda_security_group_id  = var.vpc_adoption == "existing" && var.lambda_security_group_id != "" ? var.lambda_security_group_id : module.security.lambda_security_group_id
  secrets_manager_arns      = module.security.secrets_manager_arns
  dynamodb_table_arns       = module.storage.dynamodb_table_arns
  s3_bucket_arns           = module.storage.s3_bucket_arns
  
  tags = local.common_tags
}

module "monitoring" {
  source = "../../modules/monitoring"
  
  environment   = var.environment
  deployment_id = local.deployment_id
  project_name  = var.project_name
  
  # CloudWatch Configuration
  log_retention_days = var.log_retention_days
  enable_detailed_monitoring = var.enable_detailed_monitoring
  
  # Alerting Configuration
  alert_email_addresses         = var.alert_email_addresses
  trading_alert_email_addresses = var.trading_alert_email_addresses
  critical_alert_email_addresses = var.critical_alert_email_addresses
  
  # Notification Channels
  discord_webhook_url = var.discord_webhook_url
  telegram_bot_token  = var.telegram_bot_token
  
  # Cost Monitoring
  cost_alert_threshold = var.monthly_cost_alert_threshold
  cost_alert_email    = var.cost_alert_email
  
  # Performance Monitoring
  api_gateway_id      = module.compute.api_gateway_id
  lambda_function_arns = module.compute.lambda_function_arns
  dynamodb_table_names = module.storage.dynamodb_table_names
  cloudfront_distribution_id = module.compute.cloudfront_distribution_id
  
  # X-Ray Tracing
  enable_xray_tracing = var.enable_xray_tracing
  
  tags = local.common_tags
}

# Local values for Lambda environment variables
locals {
  lambda_environment = {
    ENVIRONMENT                   = var.environment
    AWS_REGION                   = var.aws_region
    LOG_LEVEL                    = var.log_level
    DEPLOYMENT_ID                = local.deployment_id
    
    # API Configuration
    API_GATEWAY_URL              = module.compute.api_gateway_url
    CORS_ALLOWED_ORIGINS         = join(",", var.cors_allowed_origins)
    
    # Database Configuration
    DYNAMODB_TABLE_PREFIX        = "${var.project_name}-${var.environment}"
    DYNAMODB_USERS_TABLE         = module.storage.dynamodb_table_names["users"]
    DYNAMODB_POSITIONS_TABLE     = module.storage.dynamodb_table_names["positions"]
    DYNAMODB_SIGNALS_TABLE       = module.storage.dynamodb_table_names["signals"]
    DYNAMODB_CANDLES_TABLE       = module.storage.dynamodb_table_names["live_candles"]
    DYNAMODB_PORTFOLIOS_TABLE    = module.storage.dynamodb_table_names["virtual_portfolios"]
    DYNAMODB_TRANSACTIONS_TABLE  = module.storage.dynamodb_table_names["virtual_transactions"]
    DYNAMODB_PERFORMANCE_TABLE   = module.storage.dynamodb_table_names["model_performance"]
    DYNAMODB_CONFIG_TABLE        = module.storage.dynamodb_table_names["system_config"]
    
    # S3 Configuration
    S3_FRONTEND_BUCKET          = module.storage.s3_bucket_ids["frontend"]
    S3_DATA_BUCKET              = module.storage.s3_bucket_ids["data"]
    S3_MODELS_BUCKET            = module.storage.s3_bucket_ids["models"]
    S3_BACKUPS_BUCKET           = module.storage.s3_bucket_ids["backups"]
    
    # Security Configuration (using pre-existing consolidated secret)
    SECRETS_MANAGER_NAME        = "tradepulse/trading-secrets-production"
    
    # Trading Configuration
    SUPPORTED_SYMBOLS           = join(",", var.supported_symbols)
    TRADING_INTERVALS           = join(",", var.trading_intervals)
    ENABLE_LIVE_TRADING         = var.enable_live_trading ? "true" : "false"
    MAX_POSITION_SIZE_USD       = tostring(var.max_position_size_usd)
    RISK_MANAGEMENT_ENABLED     = var.risk_management_enabled ? "true" : "false"
    
    # Feature Flags
    ENABLE_ADVANCED_ANALYTICS   = var.enable_advanced_analytics ? "true" : "false"
    ENABLE_ML_CONTINUOUS_LEARNING = var.enable_ml_continuous_learning ? "true" : "false"
    ENABLE_SOCIAL_TRADING       = var.enable_social_trading ? "true" : "false"
    ENABLE_PORTFOLIO_SHOWCASE   = var.enable_portfolio_showcase ? "true" : "false"
    ENABLE_DEBUG_MODE           = var.enable_debug_mode ? "true" : "false"
    
    # Monitoring
    ENABLE_XRAY_TRACING         = var.enable_xray_tracing ? "true" : "false"
    ENABLE_DETAILED_MONITORING  = var.enable_detailed_monitoring ? "true" : "false"
  }
}