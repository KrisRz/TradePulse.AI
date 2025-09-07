# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/stepfunctions/${var.app_name}-${var.env}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# IAM role for Step Functions
resource "aws_iam_role" "step_functions" {
  name = "${var.app_name}-${var.env}-stepfunctions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM policy for Step Functions to invoke Lambda functions
resource "aws_iam_role_policy" "step_functions_lambda" {
  name = "${var.app_name}-${var.env}-stepfunctions-lambda-policy"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          "${var.feature_engineering_lambda_arn}",
          "${var.ai_inference_lambda_arn}",
          "${var.ensemble_aggregator_lambda_arn}",
          "${var.risk_assessment_lambda_arn}",
          "${var.signal_generator_lambda_arn}",
          "${var.data_preparation_lambda_arn}",
          "${var.model_training_lambda_arn}",
          "${var.model_validation_lambda_arn}",
          "${var.model_deployment_lambda_arn}",
          "${var.position_closer_lambda_arn}",
          "${var.notification_lambda_arn}",
          "${var.audit_logger_lambda_arn}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# AI Trading Signal Generation Pipeline
resource "aws_sfn_state_machine" "ai_pipeline" {
  name     = "${var.app_name}-${var.env}-ai-pipeline"
  role_arn = aws_iam_role.step_functions.arn
  type     = "EXPRESS" # For high-frequency trading

  definition = templatefile("${path.module}/definitions/ai_pipeline.json", {
    feature_engineering_arn = var.feature_engineering_lambda_arn
    ai_inference_arn        = var.ai_inference_lambda_arn
    ensemble_aggregator_arn = var.ensemble_aggregator_lambda_arn
    risk_assessment_arn     = var.risk_assessment_lambda_arn
    signal_generator_arn    = var.signal_generator_lambda_arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = var.tags
}

# Model Retraining Pipeline (runs daily)
resource "aws_sfn_state_machine" "model_retraining" {
  name     = "${var.app_name}-${var.env}-model-retraining"
  role_arn = aws_iam_role.step_functions.arn
  type     = "STANDARD" # For long-running processes

  definition = templatefile("${path.module}/definitions/model_retraining.json", {
    data_preparation_arn = var.data_preparation_lambda_arn
    model_training_arn   = var.model_training_lambda_arn
    model_validation_arn = var.model_validation_lambda_arn
    model_deployment_arn = var.model_deployment_lambda_arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = var.tags
}

# Emergency Trading Halt Pipeline
resource "aws_sfn_state_machine" "emergency_halt" {
  name     = "${var.app_name}-${var.env}-emergency-halt"
  role_arn = aws_iam_role.step_functions.arn
  type     = "EXPRESS" # For immediate response

  definition = templatefile("${path.module}/definitions/emergency_halt.json", {
    position_closer_arn = var.position_closer_lambda_arn
    notification_arn    = var.notification_lambda_arn
    audit_logger_arn    = var.audit_logger_lambda_arn
  })

  tags = var.tags
}
