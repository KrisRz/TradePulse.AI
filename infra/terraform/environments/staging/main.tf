# TradePulse.AI - Staging Environment Infrastructure
# Cost-optimized staging environment for testing and development

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
  
  # Remote state management for staging
  backend "s3" {
    bucket         = "tradepulse-terraform-state-staging"
    key            = "staging/terraform.tfstate"
    region         = "eu-west-2"
    encrypt        = true
    dynamodb_table = "tradepulse-terraform-locks"
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project           = "TradePulse.AI"
      Environment       = "staging"
      ManagedBy         = "Terraform"
      Owner            = "TradePulse-AI-Team"
      CostCenter       = "staging-testing"
      Purpose          = "development-testing"
      AutoShutdown     = "enabled"
    }
  }
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
    Environment  = "staging"
    CostOptimized = "true"
  }
}

# Use production modules with staging-specific configurations
module "networking" {
  source = "../../modules/networking"
  
  environment    = var.environment
  deployment_id  = local.deployment_id
  aws_region     = var.aws_region
  
  # Simpler networking for staging
  vpc_cidr           = var.vpc_cidr
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2) # Only 2 AZs for cost savings
  
  # Security (less restrictive for testing)
  allowed_cidr_blocks = var.allowed_cidr_blocks
  enable_vpc_flow_logs = false  # Disabled for cost savings
  
  tags = local.common_tags
}

module "security" {
  source = "../../modules/security"
  
  environment   = var.environment
  deployment_id = local.deployment_id
  project_name  = var.project_name
  
  # Simplified security for staging
  enable_waf           = false  # Disabled for cost savings
  rate_limit_per_ip    = var.api_rate_limit
  allowed_cidr_blocks  = var.allowed_cidr_blocks
  
  # Test secrets (not production values)
  secrets_config = {
    binance_api_key    = var.binance_api_key
    binance_secret_key = var.binance_secret_key
    jwt_secret_key     = var.jwt_secret_key
  }
  
  domain_name = ""  # No custom domain for staging
  
  tags = local.common_tags
}

module "storage" {
  source = "../../modules/storage"
  
  environment   = var.environment
  deployment_id = local.deployment_id
  project_name  = var.project_name
  
  # Minimal DynamoDB configuration for staging
  tables_config = {
    users = {
      hash_key           = "user_id"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = false  # Disabled for cost savings
      enable_pitr        = false  # Disabled for cost savings
      enable_streams     = false
      global_tables      = false
    }
    
    positions = {
      hash_key           = "position_id"
      range_key          = "timestamp"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = false
      enable_pitr        = false
      enable_streams     = true   # Keep streams for testing
      ttl_attribute      = "expires_at"
      global_tables      = false
    }
    
    signals = {
      hash_key           = "signal_id"
      range_key          = "created_at"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = false
      enable_pitr        = false
      enable_streams     = true
      ttl_attribute      = "expires_at"
      global_tables      = false
    }
    
    live_candles = {
      hash_key           = "symbol_interval"
      range_key          = "timestamp"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = false
      enable_pitr        = false
      enable_streams     = false
      ttl_attribute      = "expires_at"
      global_tables      = false
    }
    
    # Minimal tables for staging
    virtual_portfolios = {
      hash_key           = "portfolio_id"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = false
      enable_pitr        = false
      enable_streams     = false
      global_tables      = false
    }
    
    system_config = {
      hash_key           = "config_key"
      billing_mode       = "PAY_PER_REQUEST"
      enable_encryption  = false
      enable_pitr        = false
      enable_streams     = false
      global_tables      = false
    }
  }
  
  # Simplified S3 configuration
  s3_buckets = {
    frontend = {
      purpose           = "static-website"
      enable_versioning = false  # Disabled for cost savings
      enable_encryption = false  # Disabled for cost savings
      enable_cors       = true
      lifecycle_rules   = []     # No lifecycle rules
    }
    
    data = {
      purpose           = "data-storage"
      enable_versioning = false
      enable_encryption = false
      enable_cors       = false
      lifecycle_rules   = []
    }
  }
  
  # Minimal backup settings
  backup_retention_days         = 7      # Short retention for staging
  enable_cross_region_backup    = false  # No cross-region backup
  enable_point_in_time_recovery = false  # Disabled for cost savings
  
  tags = local.common_tags
}

module "compute" {
  source = "../../modules/compute"
  
  environment   = var.environment
  deployment_id = local.deployment_id
  project_name  = var.project_name
  
  # Smaller Lambda configuration for staging
  lambda_functions = {
    backend_api = {
      filename         = "../../../app/backend/backend-lambda.zip"
      handler          = "lambda_handler.handler"
      runtime          = "python3.11"
      memory_size      = 512   # Smaller memory for cost savings
      timeout          = 30
      environment_vars = local.lambda_environment
      vpc_config       = null  # No VPC for staging to save costs
    }
    
    ai_signals = {
      filename         = "../../../app/backend/ai-signals-lambda.zip"
      handler          = "ai_handler.handler"
      runtime          = "python3.11"
      memory_size      = 1024  # Smaller memory
      timeout          = 60
      environment_vars = local.lambda_environment
      vpc_config       = null
    }
    
    data_collector = {
      filename         = "../../../app/backend/data-collector-lambda.zip"
      handler          = "data_collector.handler"
      runtime          = "python3.11"
      memory_size      = 512
      timeout          = 120
      environment_vars = local.lambda_environment
      vpc_config       = null
    }
    
    health_monitor = {
      filename         = "../../../app/backend/health-monitor-lambda.zip"
      handler          = "health_monitor.handler"
      runtime          = "python3.11"
      memory_size      = 256   # Minimal memory
      timeout          = 30
      environment_vars = local.lambda_environment
      vpc_config       = null
    }
  }
  
  # Simplified API Gateway
  api_gateway_config = {
    name               = "${var.project_name}-api-staging-${local.deployment_id}"
    description        = "TradePulse.AI Staging API"
    protocol_type      = "HTTP"
    cors_enabled       = true
    throttle_burst     = 500   # Lower limits for staging
    throttle_rate      = 100
    custom_domain      = null
    certificate_arn    = null
  }
  
  # Minimal EventBridge (only essential schedules)
  eventbridge_rules = {
    health_check = {
      description         = "Health check every 10 minutes"
      schedule_expression = "rate(10 minutes)"
      target_function    = "health_monitor"
      input              = jsonencode({action = "health_check"})
    }
  }
  
  # Simple CloudFront
  cloudfront_config = {
    frontend_bucket_id     = module.storage.s3_bucket_ids["frontend"]
    frontend_bucket_domain = module.storage.s3_bucket_domains["frontend"]
    api_domain            = module.compute.api_gateway_domain
    price_class           = "PriceClass_100"  # Cheapest option
    custom_domain         = null
    certificate_arn       = null
  }
  
  # Dependencies
  vpc_id                    = var.enable_vpc ? module.networking.vpc_id : null
  public_subnet_ids         = var.enable_vpc ? module.networking.public_subnet_ids : []
  private_subnet_ids        = var.enable_vpc ? module.networking.private_subnet_ids : []
  lambda_security_group_id  = var.enable_vpc ? module.security.lambda_security_group_id : null
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
  
  # Minimal monitoring for staging
  log_retention_days = 7  # Short retention
  enable_detailed_monitoring = false  # Disabled for cost savings
  
  # Basic alerting
  alert_email_addresses         = var.alert_email_addresses
  trading_alert_email_addresses = []  # No trading alerts in staging
  critical_alert_email_addresses = var.alert_email_addresses
  
  # No external notifications for staging
  discord_webhook_url = ""
  telegram_bot_token  = ""
  
  # Higher cost threshold for staging
  cost_alert_threshold = 100  # $100 threshold
  cost_alert_email    = var.cost_alert_email
  
  # Performance monitoring (minimal)
  api_gateway_id      = module.compute.api_gateway_id
  lambda_function_arns = module.compute.lambda_function_arns
  dynamodb_table_names = module.storage.dynamodb_table_names
  cloudfront_distribution_id = module.compute.cloudfront_distribution_id
  
  # No X-Ray tracing in staging
  enable_xray_tracing = false
  
  tags = local.common_tags
}

# Staging-specific Lambda environment variables
locals {
  lambda_environment = {
    ENVIRONMENT                   = "staging"
    AWS_REGION                   = var.aws_region
    LOG_LEVEL                    = "DEBUG"  # More verbose logging for staging
    DEPLOYMENT_ID                = local.deployment_id
    
    # API Configuration
    API_GATEWAY_URL              = module.compute.api_gateway_url
    CORS_ALLOWED_ORIGINS         = "*"  # Allow all origins for testing
    
    # Database Configuration
    DYNAMODB_TABLE_PREFIX        = "${var.project_name}-staging"
    DYNAMODB_USERS_TABLE         = module.storage.dynamodb_table_names["users"]
    DYNAMODB_POSITIONS_TABLE     = module.storage.dynamodb_table_names["positions"]
    DYNAMODB_SIGNALS_TABLE       = module.storage.dynamodb_table_names["signals"]
    DYNAMODB_CANDLES_TABLE       = module.storage.dynamodb_table_names["live_candles"]
    DYNAMODB_PORTFOLIOS_TABLE    = module.storage.dynamodb_table_names["virtual_portfolios"]
    DYNAMODB_CONFIG_TABLE        = module.storage.dynamodb_table_names["system_config"]
    
    # S3 Configuration
    S3_FRONTEND_BUCKET          = module.storage.s3_bucket_ids["frontend"]
    S3_DATA_BUCKET              = module.storage.s3_bucket_ids["data"]
    
    # Security Configuration
    SECRETS_MANAGER_PREFIX      = "${var.project_name}/staging"
    BINANCE_API_KEY_SECRET      = module.security.secrets_manager_names["binance_api_key"]
    BINANCE_SECRET_KEY_SECRET   = module.security.secrets_manager_names["binance_secret_key"]
    JWT_SECRET_KEY_SECRET       = module.security.secrets_manager_names["jwt_secret_key"]
    
    # Trading Configuration (test mode)
    SUPPORTED_SYMBOLS           = "BTCUSDT,ETHUSDT"  # Limited symbols for testing
    TRADING_INTERVALS           = "1m,5m,1h"         # Limited intervals
    ENABLE_LIVE_TRADING         = "false"            # Never enable live trading in staging
    MAX_POSITION_SIZE_USD       = "100"              # Small test amounts
    RISK_MANAGEMENT_ENABLED     = "true"
    
    # Feature Flags (enable all for testing)
    ENABLE_ADVANCED_ANALYTICS   = "true"
    ENABLE_ML_CONTINUOUS_LEARNING = "false"  # Disabled to save costs
    ENABLE_SOCIAL_TRADING       = "true"
    ENABLE_PORTFOLIO_SHOWCASE   = "true"
    ENABLE_DEBUG_MODE           = "true"     # Enable debug mode in staging
    
    # Monitoring
    ENABLE_XRAY_TRACING         = "false"   # Disabled for cost savings
    ENABLE_DETAILED_MONITORING  = "false"   # Disabled for cost savings
  }
}