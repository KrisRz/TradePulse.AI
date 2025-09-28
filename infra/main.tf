terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "tradepulse-terraform-state-590183672693"
    key    = "terraform.tfstate"
    region = "eu-west-2"
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Repository  = var.github_repo
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ECR Repository for backend images
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }


  tags = {
    Name = "${var.project_name}-backend-ecr"
  }
}

# ECR Lifecycle Policy (separate resource)
resource "aws_ecr_lifecycle_policy" "backend_lifecycle" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 20 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# ECR Repository policy for GitHub Actions
resource "aws_ecr_repository_policy" "backend_policy" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowGitHubActions"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.github_actions.arn
        }
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
      }
    ]
  })
}

# Outputs
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.backend.repository_url
}

output "app_runner_service_url" {
  description = "App Runner service URL"
  value       = aws_apprunner_service.backend.service_url
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    signals     = aws_dynamodb_table.signals.name
    portfolio   = aws_dynamodb_table.portfolio.name
    positions   = aws_dynamodb_table.positions.name
    analytics   = aws_dynamodb_table.analytics.name
    brain_state = aws_dynamodb_table.brain_state.name
    runtime     = aws_dynamodb_table.runtime.name
    market_data = aws_dynamodb_table.market_data.name
  }
}

output "github_role_arn" {
  description = "GitHub Actions IAM role ARN"
  value       = aws_iam_role.github_actions.arn
}
