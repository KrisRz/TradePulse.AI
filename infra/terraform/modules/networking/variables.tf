# TradePulse.AI - Networking Module Variables
# Professional variable definitions for network resources

variable "environment" {
  description = "Environment name (production/staging)"
  type        = string
}

variable "deployment_id" {
  description = "Unique deployment identifier"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

# ============================================================================
# VPC CONFIGURATION
# ============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  
  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least 2 availability zones must be provided for high availability."
  }
}

# ============================================================================
# NETWORK ARCHITECTURE OPTIONS
# ============================================================================

variable "enable_single_nat_gateway" {
  description = "Use a single NAT Gateway for all private subnets (cost optimization)"
  type        = bool
  default     = false
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services"
  type        = bool
  default     = true
}

variable "enable_api_gateway_vpc_endpoint" {
  description = "Enable VPC endpoint for API Gateway"
  type        = bool
  default     = false
}

variable "enable_database_security_group" {
  description = "Create security group for database access (future use)"
  type        = bool
  default     = false
}

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access resources"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_vpc_flow_logs" {
  description = "Enable VPC Flow Logs for network monitoring"
  type        = bool
  default     = true
}

variable "flow_logs_retention_days" {
  description = "Retention period for VPC Flow Logs in days"
  type        = number
  default     = 30
  
  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.flow_logs_retention_days)
    error_message = "Flow logs retention days must be a valid CloudWatch retention period."
  }
}

# ============================================================================
# TAGS
# ============================================================================

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}