terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "region" {
  type    = string
  default = "eu-west-2"
}

variable "env" {
  type    = string
  default = "prod"
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      App       = "TradePulse.AI"
      Env       = var.env
      ManagedBy = "Terraform"
    }
  }
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
