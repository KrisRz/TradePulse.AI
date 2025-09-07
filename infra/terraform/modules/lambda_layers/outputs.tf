output "ml_base_layer_arn" {
  description = "ARN of ML base layer"
  value       = aws_lambda_layer_version.ml_base.arn
}

output "tensorflow_layer_arn" {
  description = "ARN of TensorFlow layer"
  value       = aws_lambda_layer_version.tensorflow.arn
}

output "xgboost_layer_arn" {
  description = "ARN of XGBoost layer"
  value       = aws_lambda_layer_version.xgboost.arn
}

output "trading_models_layer_arn" {
  description = "ARN of trading models layer"
  value       = aws_lambda_layer_version.trading_models.arn
}

output "api_dependencies_layer_arn" {
  description = "ARN of API dependencies layer"
  value       = aws_lambda_layer_version.api_dependencies.arn
}

output "binance_client_layer_arn" {
  description = "ARN of Binance client layer"
  value       = aws_lambda_layer_version.binance_client.arn
}

# Convenient layer combinations
output "ai_processing_layers" {
  description = "List of layer ARNs for AI processing functions"
  value = [
    aws_lambda_layer_version.ml_base.arn,
    aws_lambda_layer_version.tensorflow.arn,
    aws_lambda_layer_version.xgboost.arn,
    aws_lambda_layer_version.trading_models.arn
  ]
}

output "api_layers" {
  description = "List of layer ARNs for API functions"
  value = [
    aws_lambda_layer_version.api_dependencies.arn,
    aws_lambda_layer_version.binance_client.arn
  ]
}

output "all_layer_arns" {
  description = "Map of all layer ARNs"
  value = {
    ml_base          = aws_lambda_layer_version.ml_base.arn
    tensorflow       = aws_lambda_layer_version.tensorflow.arn
    xgboost          = aws_lambda_layer_version.xgboost.arn
    trading_models   = aws_lambda_layer_version.trading_models.arn
    api_dependencies = aws_lambda_layer_version.api_dependencies.arn
    binance_client   = aws_lambda_layer_version.binance_client.arn
  }
}
