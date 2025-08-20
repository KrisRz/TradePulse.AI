# TradePulse.AI - Networking Module Outputs
# Professional output definitions for network resources

# ============================================================================
# VPC OUTPUTS
# ============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_arn" {
  description = "ARN of the VPC"
  value       = aws_vpc.main.arn
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC (alias)"
  value       = aws_vpc.main.cidr_block
}

output "vpc_enable_dns_hostnames" {
  description = "Whether DNS hostnames are enabled for the VPC"
  value       = aws_vpc.main.enable_dns_hostnames
}

output "vpc_enable_dns_support" {
  description = "Whether DNS support is enabled for the VPC"
  value       = aws_vpc.main.enable_dns_support
}

# ============================================================================
# INTERNET GATEWAY OUTPUTS
# ============================================================================

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "internet_gateway_arn" {
  description = "ARN of the Internet Gateway"
  value       = aws_internet_gateway.main.arn
}

# ============================================================================
# SUBNET OUTPUTS
# ============================================================================

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "public_subnet_arns" {
  description = "ARNs of public subnets"
  value       = aws_subnet.public[*].arn
}

output "public_subnet_cidrs" {
  description = "CIDR blocks of public subnets"
  value       = aws_subnet.public[*].cidr_block
}

output "public_subnet_azs" {
  description = "Availability zones of public subnets"
  value       = aws_subnet.public[*].availability_zone
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "private_subnet_arns" {
  description = "ARNs of private subnets"
  value       = aws_subnet.private[*].arn
}

output "private_subnet_cidrs" {
  description = "CIDR blocks of private subnets"
  value       = aws_subnet.private[*].cidr_block
}

output "private_subnet_azs" {
  description = "Availability zones of private subnets"
  value       = aws_subnet.private[*].availability_zone
}

# ============================================================================
# NAT GATEWAY OUTPUTS
# ============================================================================

output "nat_gateway_ids" {
  description = "IDs of NAT Gateways"
  value       = aws_nat_gateway.main[*].id
}

output "nat_gateway_public_ips" {
  description = "Public IP addresses of NAT Gateways"
  value       = aws_nat_gateway.main[*].public_ip
}

output "nat_gateway_private_ips" {
  description = "Private IP addresses of NAT Gateways"
  value       = aws_nat_gateway.main[*].private_ip
}

output "elastic_ip_addresses" {
  description = "Elastic IP addresses for NAT Gateways"
  value       = aws_eip.nat[*].public_ip
}

# ============================================================================
# ROUTE TABLE OUTPUTS
# ============================================================================

output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "public_route_table_arn" {
  description = "ARN of the public route table"
  value       = aws_route_table.public.arn
}

output "private_route_table_ids" {
  description = "IDs of private route tables"
  value       = aws_route_table.private[*].id
}

output "private_route_table_arns" {
  description = "ARNs of private route tables"
  value       = aws_route_table.private[*].arn
}

# ============================================================================
# SECURITY GROUP OUTPUTS
# ============================================================================

output "lambda_security_group_id" {
  description = "ID of the Lambda security group"
  value       = aws_security_group.lambda.id
}

output "lambda_security_group_arn" {
  description = "ARN of the Lambda security group"
  value       = aws_security_group.lambda.arn
}

output "api_gateway_security_group_id" {
  description = "ID of the API Gateway security group (if created)"
  value       = try(aws_security_group.api_gateway[0].id, "")
}

output "database_security_group_id" {
  description = "ID of the database security group (if created)"
  value       = try(aws_security_group.database[0].id, "")
}

# All security group IDs for reference
output "security_group_ids" {
  description = "Map of all security group IDs"
  value = {
    lambda      = aws_security_group.lambda.id
    api_gateway = try(aws_security_group.api_gateway[0].id, "")
    database    = try(aws_security_group.database[0].id, "")
  }
}

# ============================================================================
# VPC ENDPOINT OUTPUTS
# ============================================================================

output "vpc_endpoint_s3_id" {
  description = "ID of the S3 VPC endpoint (if created)"
  value       = try(aws_vpc_endpoint.s3[0].id, "")
}

output "vpc_endpoint_dynamodb_id" {
  description = "ID of the DynamoDB VPC endpoint (if created)"
  value       = try(aws_vpc_endpoint.dynamodb[0].id, "")
}

output "vpc_endpoint_lambda_id" {
  description = "ID of the Lambda VPC endpoint (if created)"
  value       = try(aws_vpc_endpoint.lambda[0].id, "")
}

output "vpc_endpoint_secretsmanager_id" {
  description = "ID of the Secrets Manager VPC endpoint (if created)"
  value       = try(aws_vpc_endpoint.secretsmanager[0].id, "")
}

# Map of all VPC endpoints
output "vpc_endpoints" {
  description = "Map of VPC endpoint IDs"
  value = {
    s3             = try(aws_vpc_endpoint.s3[0].id, "")
    dynamodb       = try(aws_vpc_endpoint.dynamodb[0].id, "")
    lambda         = try(aws_vpc_endpoint.lambda[0].id, "")
    secretsmanager = try(aws_vpc_endpoint.secretsmanager[0].id, "")
  }
}

# ============================================================================
# VPC FLOW LOGS OUTPUTS
# ============================================================================

output "vpc_flow_log_id" {
  description = "ID of the VPC Flow Log (if enabled)"
  value       = try(aws_flow_log.vpc[0].id, "")
}

output "vpc_flow_log_group_name" {
  description = "Name of the VPC Flow Logs CloudWatch log group (if enabled)"
  value       = try(aws_cloudwatch_log_group.vpc_flow_logs[0].name, "")
}

output "vpc_flow_log_group_arn" {
  description = "ARN of the VPC Flow Logs CloudWatch log group (if enabled)"
  value       = try(aws_cloudwatch_log_group.vpc_flow_logs[0].arn, "")
}

# ============================================================================
# NETWORK ACL OUTPUTS
# ============================================================================

output "public_network_acl_id" {
  description = "ID of the public network ACL"
  value       = aws_network_acl.public.id
}

output "private_network_acl_id" {
  description = "ID of the private network ACL"
  value       = aws_network_acl.private.id
}

# ============================================================================
# AVAILABILITY ZONE INFORMATION
# ============================================================================

output "availability_zones" {
  description = "List of availability zones used"
  value       = var.availability_zones
}

output "availability_zones_count" {
  description = "Number of availability zones"
  value       = length(var.availability_zones)
}

# ============================================================================
# NETWORK CONFIGURATION SUMMARY
# ============================================================================

output "network_config_summary" {
  description = "Summary of network configuration"
  value = {
    vpc_cidr                    = var.vpc_cidr
    availability_zones_count    = length(var.availability_zones)
    public_subnets_count       = length(aws_subnet.public)
    private_subnets_count      = length(aws_subnet.private)
    nat_gateways_count         = length(aws_nat_gateway.main)
    single_nat_gateway         = var.enable_single_nat_gateway
    vpc_endpoints_enabled      = var.enable_vpc_endpoints
    vpc_flow_logs_enabled      = var.enable_vpc_flow_logs
    security_groups_created    = {
      lambda      = true
      api_gateway = var.enable_api_gateway_vpc_endpoint
      database    = var.enable_database_security_group
    }
  }
}

# ============================================================================
# COST INFORMATION
# ============================================================================

output "cost_factors" {
  description = "Network-related cost factors"
  value = {
    nat_gateways_count          = length(aws_nat_gateway.main)
    elastic_ips_count           = length(aws_eip.nat)
    interface_endpoints_count   = (var.enable_vpc_endpoints ? 2 : 0) + (var.enable_api_gateway_vpc_endpoint ? 1 : 0)  # lambda + secretsmanager + optional apigw
    gateway_endpoints_count     = var.enable_vpc_endpoints ? 2 : 0  # s3 + dynamodb
    vpc_flow_logs_enabled      = var.enable_vpc_flow_logs
    estimated_monthly_nat_cost = length(aws_nat_gateway.main) * 32  # ~$32/month per NAT Gateway
  }
}

# ============================================================================
# SUBNET MAPPING FOR APPLICATIONS
# ============================================================================

output "subnet_mapping" {
  description = "Subnet mapping for different application tiers"
  value = {
    # For load balancers and public-facing resources
    public_subnets = {
      ids   = aws_subnet.public[*].id
      cidrs = aws_subnet.public[*].cidr_block
      azs   = aws_subnet.public[*].availability_zone
    }
    
    # For Lambda functions and private resources
    private_subnets = {
      ids   = aws_subnet.private[*].id
      cidrs = aws_subnet.private[*].cidr_block
      azs   = aws_subnet.private[*].availability_zone
    }
    
    # For database subnets (subset of private subnets)
    database_subnets = {
      ids   = aws_subnet.private[*].id  # Can be customized later
      cidrs = aws_subnet.private[*].cidr_block
      azs   = aws_subnet.private[*].availability_zone
    }
  }
}

# ============================================================================
# CONNECTIVITY INFORMATION
# ============================================================================

output "connectivity_info" {
  description = "Network connectivity information"
  value = {
    internet_access = {
      public_subnets  = "Direct via Internet Gateway"
      private_subnets = "Via NAT Gateway"
    }
    
    aws_services_access = {
      s3_access       = var.enable_vpc_endpoints ? "Via VPC Endpoint" : "Via NAT Gateway"
      dynamodb_access = var.enable_vpc_endpoints ? "Via VPC Endpoint" : "Via NAT Gateway"
      lambda_access   = var.enable_vpc_endpoints ? "Via VPC Endpoint" : "Via NAT Gateway"
      secrets_access  = var.enable_vpc_endpoints ? "Via VPC Endpoint" : "Via NAT Gateway"
    }
    
    security = {
      network_acls    = "Configured for public and private subnets"
      security_groups = "Lambda security group created"
      flow_logs       = var.enable_vpc_flow_logs ? "Enabled" : "Disabled"
    }
  }
}