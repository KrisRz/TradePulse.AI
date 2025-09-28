# IAM roles and policies for TradePulse.AI

# GitHub Actions OIDC Identity Provider
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
  ]

  tags = {
    Name = "${var.project_name}-github-oidc"
  }
}

# GitHub Actions IAM Role
resource "aws_iam_role" "github_actions" {
  name = "${var.project_name}-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:ref:refs/heads/${var.github_branch}"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-github-actions-role"
  }
}

# GitHub Actions Policy - ECR and App Runner permissions
resource "aws_iam_policy" "github_actions_policy" {
  name = "${var.project_name}-github-actions-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRPermissions"
        Effect = "Allow"
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
        Resource = ["*"]
      },
      {
        Sid    = "AppRunnerPermissions"
        Effect = "Allow"
        Action = [
          "apprunner:DescribeService",
          "apprunner:UpdateService",
          "apprunner:ListOperations"
        ]
        Resource = ["*"]
      },
      {
        Sid    = "TerraformStatePermissions"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = ["arn:aws:s3:::${var.project_name}-terraform-state/*"]
      },
      {
        Sid    = "TerraformLockPermissions"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = ["arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.project_name}-terraform-locks"]
      },
      {
        Sid    = "TerraformManagementPermissions"
        Effect = "Allow"
        Action = [
          "iam:*",
          "apprunner:*",
          "ecr:*",
          "dynamodb:*",
          "ssm:*",
          "logs:*",
          "cloudwatch:*",
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeInternetGateways",
          "ec2:DescribeNatGateways",
          "ec2:DescribeRouteTables",
          "ec2:DescribeVpcEndpoints"
        ]
        Resource = ["*"]
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-github-actions-policy"
  }
}

resource "aws_iam_role_policy_attachment" "github_actions_policy" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.github_actions_policy.arn
}

# App Runner Instance Role
resource "aws_iam_role" "app_runner_instance" {
  name = "${var.project_name}-app-runner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-app-runner-instance-role"
  }
}

# App Runner Instance Policy
resource "aws_iam_policy" "app_runner_instance_policy" {
  name = "${var.project_name}-app-runner-instance-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SSMParameterAccess"
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/${var.environment}/*"
        ]
      },
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:DescribeTable",
          "dynamodb:DescribeStream",
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:ListStreams"
        ]
        Resource = [
          "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.project_name}_*",
          "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.project_name}_*/index/*"
        ]
      },
      {
        Sid    = "DynamoDBListTables"
        Effect = "Allow"
        Action = [
          "dynamodb:ListTables"
        ]
        Resource = ["*"]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/apprunner/${var.project_name}-*:*"
        ]
      },
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = ["*"]
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "TradePulse.AI"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-app-runner-instance-policy"
  }
}

resource "aws_iam_role_policy_attachment" "app_runner_instance_policy" {
  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.app_runner_instance_policy.arn
}

# App Runner Access Role (for pulling from ECR)
resource "aws_iam_role" "app_runner_access" {
  name = "${var.project_name}-app-runner-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-app-runner-access-role"
  }
}

# Attach the AWS managed policy for App Runner ECR access
resource "aws_iam_role_policy_attachment" "app_runner_ecr_policy" {
  role       = aws_iam_role.app_runner_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}
