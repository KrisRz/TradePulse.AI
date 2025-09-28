# VPC and networking resources for TradePulse.AI
# Optional VPC for private networking (can be disabled)

resource "aws_vpc" "main" {
  count = var.enable_vpc ? 1 : 0
  
  cidr_block           = "10.20.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_subnet" "private_a" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id            = aws_vpc.main[0].id
  cidr_block        = "10.20.1.0/24"
  availability_zone = "${var.region}a"

  tags = {
    Name = "${var.project_name}-private-subnet-a"
    Type = "Private"
  }
}

resource "aws_subnet" "private_b" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id            = aws_vpc.main[0].id
  cidr_block        = "10.20.2.0/24"
  availability_zone = "${var.region}b"

  tags = {
    Name = "${var.project_name}-private-subnet-b"
    Type = "Private"
  }
}

# Internet Gateway for outbound traffic
resource "aws_internet_gateway" "main" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id = aws_vpc.main[0].id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# NAT Gateway for private subnet outbound access
resource "aws_eip" "nat" {
  count = var.enable_vpc ? 1 : 0
  
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  count = var.enable_vpc ? 1 : 0
  
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.private_a[0].id

  tags = {
    Name = "${var.project_name}-nat-gateway"
  }

  depends_on = [aws_internet_gateway.main]
}

# Route table for private subnets
resource "aws_route_table" "private" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[0].id
  }

  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

# Associate private subnets with route table
resource "aws_route_table_association" "private_a" {
  count = var.enable_vpc ? 1 : 0
  
  subnet_id      = aws_subnet.private_a[0].id
  route_table_id = aws_route_table.private[0].id
}

resource "aws_route_table_association" "private_b" {
  count = var.enable_vpc ? 1 : 0
  
  subnet_id      = aws_subnet.private_b[0].id
  route_table_id = aws_route_table.private[0].id
}

# Security group for App Runner VPC Connector
resource "aws_security_group" "app_runner" {
  count = var.enable_vpc ? 1 : 0
  
  name_prefix = "${var.project_name}-apprunner-"
  description = "Security group for App Runner VPC Connector"
  vpc_id      = aws_vpc.main[0].id

  # Outbound rules
  egress {
    description = "HTTPS to internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "HTTP to internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "WebSocket to Binance"
    from_port   = 9443
    to_port     = 9443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-apprunner-sg"
  }
}

# VPC Connector for App Runner
resource "aws_apprunner_vpc_connector" "main" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_connector_name = "${var.project_name}-vpc-connector"
  subnets            = [aws_subnet.private_a[0].id, aws_subnet.private_b[0].id]
  security_groups    = [aws_security_group.app_runner[0].id]

  tags = {
    Name = "${var.project_name}-vpc-connector"
  }
}

# S3 VPC Endpoint (for potential future use)
resource "aws_vpc_endpoint" "s3" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id            = aws_vpc.main[0].id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private[0].id]

  tags = {
    Name = "${var.project_name}-s3-endpoint"
  }
}
