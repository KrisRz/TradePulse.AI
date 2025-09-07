variable "app_name" {
  description = "Application name"
  type        = string
}

variable "env" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "layers_bucket" {
  description = "S3 bucket for Lambda layers"
  type        = string
}

variable "model_version" {
  description = "Version of trading models"
  type        = string
  default     = "v1.0.0"
}

variable "auto_upload_layers" {
  description = "Whether to automatically upload layer files to S3"
  type        = bool
  default     = false
}

# Layer file paths (when auto_upload_layers is true)
variable "ml_base_layer_path" {
  description = "Local path to ML base layer ZIP file"
  type        = string
  default     = ""
}

variable "tensorflow_layer_path" {
  description = "Local path to TensorFlow layer ZIP file"
  type        = string
  default     = ""
}

variable "xgboost_layer_path" {
  description = "Local path to XGBoost layer ZIP file"
  type        = string
  default     = ""
}

variable "trading_models_layer_path" {
  description = "Local path to trading models layer ZIP file"
  type        = string
  default     = ""
}

variable "api_dependencies_layer_path" {
  description = "Local path to API dependencies layer ZIP file"
  type        = string
  default     = ""
}

variable "binance_client_layer_path" {
  description = "Local path to Binance client layer ZIP file"
  type        = string
  default     = ""
}
