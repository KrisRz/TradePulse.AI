# TradePulse.AI - Networking Module
# VPC, Subnets, Security Groups, NAT Gateway
# Enterprise-grade network infrastructure

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}-${var.deployment_id}"
  
  # Calculate subnet CIDRs
  subnet_count = length(var.availability_zones)
  public_subnets = [
    for i in range(local.subnet_count) : 
    cidrsubnet(var.vpc_cidr, 8, i)
  ]
  private_subnets = [
    for i in range(local.subnet_count) : 
    cidrsubnet(var.vpc_cidr, 8, i + local.subnet_count)
  ]
  
  common_tags = merge(var.tags, {
    Module = "networking"
    Service = "vpc-networking"
  })
}

# ============================================================================
# VPC CONFIGURATION
# ============================================================================

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-vpc"
    Type = "main-vpc"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-igw"
    Type = "internet-gateway"
  })
}

# ============================================================================
# PUBLIC SUBNETS
# ============================================================================

resource "aws_subnet" "public" {
  count = local.subnet_count
  
  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnets[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-public-subnet-${count.index + 1}"
    Type = "public-subnet"
    AZ   = var.availability_zones[count.index]
  })
}

# Public route table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-public-rt"
    Type = "public-route-table"
  })
}

# Public route table associations
resource "aws_route_table_association" "public" {
  count = local.subnet_count
  
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ============================================================================
# PRIVATE SUBNETS
# ============================================================================

resource "aws_subnet" "private" {
  count = local.subnet_count
  
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnets[count.index]
  availability_zone = var.availability_zones[count.index]
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-subnet-${count.index + 1}"
    Type = "private-subnet"
    AZ   = var.availability_zones[count.index]
  })
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count = var.enable_single_nat_gateway ? 1 : local.subnet_count
  
  domain = "vpc"
  
  depends_on = [aws_internet_gateway.main]
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat-eip-${count.index + 1}"
    Type = "nat-gateway-eip"
  })
}

# NAT Gateways
resource "aws_nat_gateway" "main" {
  count = var.enable_single_nat_gateway ? 1 : local.subnet_count
  
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  
  depends_on = [aws_internet_gateway.main]
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat-gateway-${count.index + 1}"
    Type = "nat-gateway"
    AZ   = var.availability_zones[count.index]
  })
}

# Private route tables
resource "aws_route_table" "private" {
  count = var.enable_single_nat_gateway ? 1 : local.subnet_count
  
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-rt-${count.index + 1}"
    Type = "private-route-table"
  })
}

# Private route table associations
resource "aws_route_table_association" "private" {
  count = local.subnet_count
  
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[var.enable_single_nat_gateway ? 0 : count.index].id
}

# ============================================================================
# SECURITY GROUPS
# ============================================================================

# Lambda security group
resource "aws_security_group" "lambda" {
  name        = "${local.name_prefix}-lambda-sg"
  description = "Security group for Lambda functions"
  vpc_id      = aws_vpc.main.id
  
  # Outbound rules
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # HTTPS outbound for API calls
  egress {
    description = "HTTPS outbound"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # HTTP outbound for API calls
  egress {
    description = "HTTP outbound"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-lambda-sg"
    Type = "lambda-security-group"
  })
}

# API Gateway security group (if needed for VPC endpoints)
resource "aws_security_group" "api_gateway" {
  count = var.enable_api_gateway_vpc_endpoint ? 1 : 0
  
  name        = "${local.name_prefix}-apigw-sg"
  description = "Security group for API Gateway VPC endpoint"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
  
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-apigw-sg"
    Type = "api-gateway-security-group"
  })
}

# Database security group (for future RDS if needed)
resource "aws_security_group" "database" {
  count = var.enable_database_security_group ? 1 : 0
  
  name        = "${local.name_prefix}-db-sg"
  description = "Security group for database access"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    description     = "Database access from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }
  
  ingress {
    description     = "MySQL/MariaDB access from Lambda"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-sg"
    Type = "database-security-group"
  })
}

# ============================================================================
# VPC ENDPOINTS
# ============================================================================

# S3 VPC Endpoint (Gateway)
resource "aws_vpc_endpoint" "s3" {
  count = var.enable_vpc_endpoints ? 1 : 0
  
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  
  route_table_ids = concat(
    [aws_route_table.public.id],
    aws_route_table.private[*].id
  )
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-s3-endpoint"
    Type = "s3-vpc-endpoint"
  })
}

# DynamoDB VPC Endpoint (Gateway)
resource "aws_vpc_endpoint" "dynamodb" {
  count = var.enable_vpc_endpoints ? 1 : 0
  
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.dynamodb"
  vpc_endpoint_type = "Gateway"
  
  route_table_ids = concat(
    [aws_route_table.public.id],
    aws_route_table.private[*].id
  )
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-dynamodb-endpoint"
    Type = "dynamodb-vpc-endpoint"
  })
}

# Lambda VPC Endpoint (Interface)
resource "aws_vpc_endpoint" "lambda" {
  count = var.enable_vpc_endpoints ? 1 : 0
  
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.lambda"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.lambda.id]
  private_dns_enabled = true
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-lambda-endpoint"
    Type = "lambda-vpc-endpoint"
  })
}

# Secrets Manager VPC Endpoint (Interface)
resource "aws_vpc_endpoint" "secretsmanager" {
  count = var.enable_vpc_endpoints ? 1 : 0
  
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.lambda.id]
  private_dns_enabled = true
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-secretsmanager-endpoint"
    Type = "secretsmanager-vpc-endpoint"
  })
}

# ============================================================================
# VPC FLOW LOGS
# ============================================================================

resource "aws_flow_log" "vpc" {
  count = var.enable_vpc_flow_logs ? 1 : 0
  
  iam_role_arn    = aws_iam_role.flow_logs[0].arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs[0].arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-vpc-flow-logs"
    Type = "vpc-flow-logs"
  })
}

# CloudWatch Log Group for VPC Flow Logs
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  count = var.enable_vpc_flow_logs ? 1 : 0
  
  name              = "/aws/vpc/flow-logs/${local.name_prefix}"
  retention_in_days = var.flow_logs_retention_days
  
  tags = local.common_tags
}

# IAM role for VPC Flow Logs
resource "aws_iam_role" "flow_logs" {
  count = var.enable_vpc_flow_logs ? 1 : 0
  
  name = "${local.name_prefix}-flow-logs-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# IAM policy for VPC Flow Logs
resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_vpc_flow_logs ? 1 : 0
  
  name = "${local.name_prefix}-flow-logs-policy"
  role = aws_iam_role.flow_logs[0].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# ============================================================================
# NETWORK ACLs
# ============================================================================

# Public Network ACL
resource "aws_network_acl" "public" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.public[*].id
  
  # Inbound rules
  ingress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 80
    to_port    = 80
  }
  
  ingress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 443
    to_port    = 443
  }
  
  ingress {
    protocol   = "tcp"
    rule_no    = 120
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 1024
    to_port    = 65535
  }
  
  # Outbound rules
  egress {
    protocol   = "-1"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-public-nacl"
    Type = "public-network-acl"
  })
}

# Private Network ACL
resource "aws_network_acl" "private" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.private[*].id
  
  # Inbound rules
  ingress {
    protocol   = "-1"
    rule_no    = 100
    action     = "allow"
    cidr_block = var.vpc_cidr
    from_port  = 0
    to_port    = 0
  }
  
  ingress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 1024
    to_port    = 65535
  }
  
  # Outbound rules
  egress {
    protocol   = "-1"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-nacl"
    Type = "private-network-acl"
  })
}

# ============================================================================
# DATA SOURCES
# ============================================================================

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}