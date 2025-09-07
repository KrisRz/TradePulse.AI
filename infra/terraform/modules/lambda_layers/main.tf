# Base ML dependencies layer (NumPy, Pandas, scikit-learn)
resource "aws_lambda_layer_version" "ml_base" {
  layer_name          = "${var.app_name}-${var.env}-ml-base"
  s3_bucket           = var.layers_bucket
  s3_key              = "layers/ml-base-layer.zip"
  compatible_runtimes = ["python3.11"]
  description         = "Base ML dependencies: NumPy, Pandas, scikit-learn for TradePulse.AI"

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_s3_object.ml_base_layer]
}

# TensorFlow layer (large, separate due to size limits)
resource "aws_lambda_layer_version" "tensorflow" {
  layer_name          = "${var.app_name}-${var.env}-tensorflow"
  s3_bucket           = var.layers_bucket
  s3_key              = "layers/tensorflow-2.20.0.zip"
  compatible_runtimes = ["python3.11"]
  description         = "TensorFlow 2.20.0 for deep learning models"

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_s3_object.tensorflow_layer]
}

# XGBoost layer
resource "aws_lambda_layer_version" "xgboost" {
  layer_name          = "${var.app_name}-${var.env}-xgboost"
  s3_bucket           = var.layers_bucket
  s3_key              = "layers/xgboost-3.0.4.zip"
  compatible_runtimes = ["python3.11"]
  description         = "XGBoost 3.0.4 for gradient boosting models"

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_s3_object.xgboost_layer]
}

# Trading models layer (updated frequently)
resource "aws_lambda_layer_version" "trading_models" {
  layer_name          = "${var.app_name}-${var.env}-models"
  s3_bucket           = var.layers_bucket
  s3_key              = "layers/trading-models-${var.model_version}.zip"
  compatible_runtimes = ["python3.11"]
  description         = "Pre-trained ML models for trading signals v${var.model_version}"

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_s3_object.trading_models_layer]
}

# FastAPI + dependencies layer
resource "aws_lambda_layer_version" "api_dependencies" {
  layer_name          = "${var.app_name}-${var.env}-api-deps"
  s3_bucket           = var.layers_bucket
  s3_key              = "layers/api-dependencies.zip"
  compatible_runtimes = ["python3.11"]
  description         = "FastAPI, Pydantic, and API dependencies"

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_s3_object.api_dependencies_layer]
}

# Binance client layer
resource "aws_lambda_layer_version" "binance_client" {
  layer_name          = "${var.app_name}-${var.env}-binance"
  s3_bucket           = var.layers_bucket
  s3_key              = "layers/binance-client.zip"
  compatible_runtimes = ["python3.11"]
  description         = "Binance API client and WebSocket dependencies"

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_s3_object.binance_client_layer]
}

# S3 objects for layer ZIP files (these will be uploaded by build scripts)
resource "aws_s3_object" "ml_base_layer" {
  count  = var.auto_upload_layers ? 1 : 0
  bucket = var.layers_bucket
  key    = "layers/ml-base-layer.zip"
  source = var.ml_base_layer_path
  etag   = filemd5(var.ml_base_layer_path)
}

resource "aws_s3_object" "tensorflow_layer" {
  count  = var.auto_upload_layers ? 1 : 0
  bucket = var.layers_bucket
  key    = "layers/tensorflow-2.20.0.zip"
  source = var.tensorflow_layer_path
  etag   = filemd5(var.tensorflow_layer_path)
}

resource "aws_s3_object" "xgboost_layer" {
  count  = var.auto_upload_layers ? 1 : 0
  bucket = var.layers_bucket
  key    = "layers/xgboost-3.0.4.zip"
  source = var.xgboost_layer_path
  etag   = filemd5(var.xgboost_layer_path)
}

resource "aws_s3_object" "trading_models_layer" {
  count  = var.auto_upload_layers ? 1 : 0
  bucket = var.layers_bucket
  key    = "layers/trading-models-${var.model_version}.zip"
  source = var.trading_models_layer_path
  etag   = filemd5(var.trading_models_layer_path)
}

resource "aws_s3_object" "api_dependencies_layer" {
  count  = var.auto_upload_layers ? 1 : 0
  bucket = var.layers_bucket
  key    = "layers/api-dependencies.zip"
  source = var.api_dependencies_layer_path
  etag   = filemd5(var.api_dependencies_layer_path)
}

resource "aws_s3_object" "binance_client_layer" {
  count  = var.auto_upload_layers ? 1 : 0
  bucket = var.layers_bucket
  key    = "layers/binance-client.zip"
  source = var.binance_client_layer_path
  etag   = filemd5(var.binance_client_layer_path)
}
