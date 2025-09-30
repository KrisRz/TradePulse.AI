# App Runner service for TradePulse.AI backend

# Auto Scaling Configuration
resource "aws_apprunner_auto_scaling_configuration_version" "backend" {
  auto_scaling_configuration_name = "${var.project_name}-backend-autoscaling"

  max_concurrency = 100 # Concurrent requests per instance
  max_size        = var.app_runner_max_size
  min_size        = var.app_runner_min_size

  tags = {
    Name = "${var.project_name}-backend-autoscaling"
  }
}

# App Runner Service
resource "aws_apprunner_service" "backend" {
  service_name = "${var.project_name}-backend"

  source_configuration {
    image_repository {
      image_identifier      = "${aws_ecr_repository.backend.repository_url}:latest"
      image_repository_type = "ECR"

      image_configuration {
        port = "9002" # TradePulse.AI backend port

        # Environment variables (non-sensitive)
        runtime_environment_variables = {
          # CRITICAL: Set environment to production so backend uses AWS DynamoDB, not localhost
          ENVIRONMENT = "production"

          AWS_REGION            = var.region
          DYNAMODB_REGION       = var.region
          DYNAMODB_TABLE_PREFIX = "${var.project_name}_"
          PROFESSIONAL_MODE     = "true"
          STRICT_LIVE_STREAM    = "false" # Allow REST API fallback while WebSocket initializes
          TRADING_SYMBOL        = "BTCUSDT"
          TRADING_MODE          = "DAY_TRADING"
          LOG_LEVEL             = "INFO"
          LOG_FORMAT            = "json"
          HEALTH_CHECK_INTERVAL = "30"

          # Override local development settings
          HOST = "0.0.0.0"
          PORT = "9002"

          # CloudWatch Heartbeat configuration
          CW_NAMESPACE = "TradePulse/Brain"
          SERVICE_NAME = "${var.project_name}-backend"
        }

        # Sensitive environment variables from SSM
        runtime_environment_secrets = {
          BINANCE_API_KEY    = aws_ssm_parameter.binance_api_key.arn
          BINANCE_API_SECRET = aws_ssm_parameter.binance_api_secret.arn
        }

        # Start command override
        start_command = "uvicorn app.backend.main:app --host 0.0.0.0 --port 9002"
      }
    }

    authentication_configuration {
      access_role_arn = aws_iam_role.app_runner_access.arn
    }

    auto_deployments_enabled = true
  }

  # Instance configuration
  instance_configuration {
    cpu               = var.app_runner_cpu
    memory            = var.app_runner_memory
    instance_role_arn = aws_iam_role.app_runner_instance.arn
  }

  # Health check configuration
  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 3
  }

  # Auto scaling configuration
  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.backend.arn

  # Network configuration (only if VPC is enabled - saves ~$45/month)
  dynamic "network_configuration" {
    for_each = var.enable_vpc ? [1] : []

    content {
      egress_configuration {
        egress_type       = "VPC"
        vpc_connector_arn = aws_apprunner_vpc_connector.main[0].arn
      }
      ingress_configuration {
        is_publicly_accessible = true
      }
    }
  }

  tags = {
    Name = "${var.project_name}-backend-service"
  }

  depends_on = [
    aws_iam_role_policy_attachment.app_runner_instance_policy,
    aws_iam_role_policy_attachment.app_runner_ecr_policy
  ]
}

# CloudWatch Log Group for App Runner
resource "aws_cloudwatch_log_group" "app_runner" {
  count = var.enable_monitoring ? 1 : 0

  name              = "/aws/apprunner/${var.project_name}-backend"
  retention_in_days = 14

  tags = {
    Name = "${var.project_name}-app-runner-logs"
  }
}

# Custom domain setup removed for initial deployment  
# Can be added later when needed
