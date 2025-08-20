# TradePulse.AI - Storage Module Providers
# Provider configuration for cross-region replication

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
      configuration_aliases = [aws.replica]
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# Main provider is configured at the root level

# Replica provider for cross-region backup (us-east-1 for EU deployments)
# This will be configured in the calling module