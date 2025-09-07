#!/bin/bash

# TradePulse.AI - Lambda Layers Build Script
# Builds all Lambda layers required for serverless deployment

set -e  # Exit on any error

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAYERS_DIR="${PROJECT_ROOT}/lambda-layers"
BUILD_DIR="${PROJECT_ROOT}/build/layers"
DIST_DIR="${PROJECT_ROOT}/dist/layers"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 TradePulse.AI - Building Lambda Layers${NC}"
echo "=================================================="

# Create directories
mkdir -p "${BUILD_DIR}"
mkdir -p "${DIST_DIR}"
mkdir -p "${LAYERS_DIR}"

# Function to create layer structure
create_layer_structure() {
    local layer_name=$1
    local layer_dir="${BUILD_DIR}/${layer_name}"
    
    echo -e "${YELLOW}📦 Creating layer structure: ${layer_name}${NC}"
    
    rm -rf "${layer_dir}"
    mkdir -p "${layer_dir}/python/lib/python3.11/site-packages"
    
    echo "${layer_dir}"
}

# Function to zip layer
zip_layer() {
    local layer_name=$1
    local layer_dir="${BUILD_DIR}/${layer_name}"
    local output_file="${DIST_DIR}/${layer_name}.zip"
    
    echo -e "${YELLOW}📦 Zipping layer: ${layer_name}${NC}"
    
    cd "${layer_dir}"
    zip -r "${output_file}" . > /dev/null
    
    local size=$(du -h "${output_file}" | cut -f1)
    echo -e "${GREEN}✅ Created ${layer_name}.zip (${size})${NC}"
    
    cd "${PROJECT_ROOT}"
}

# 1. ML Base Layer (NumPy, Pandas, scikit-learn)
echo -e "\n${BLUE}1️⃣ Building ML Base Layer${NC}"
ML_BASE_DIR=$(create_layer_structure "ml-base-layer")

cat > "${ML_BASE_DIR}/requirements.txt" << EOF
numpy>=2.1.0
pandas>=2.2.3
scikit-learn>=1.7.1
pyarrow>=17.0.0
EOF

echo "Installing ML base dependencies..."
pip install -r "${ML_BASE_DIR}/requirements.txt" \
    --target "${ML_BASE_DIR}/python/lib/python3.11/site-packages" \
    --no-deps --quiet

zip_layer "ml-base-layer"

# 2. TensorFlow Layer
echo -e "\n${BLUE}2️⃣ Building TensorFlow Layer${NC}"
TENSORFLOW_DIR=$(create_layer_structure "tensorflow-2.20.0")

cat > "${TENSORFLOW_DIR}/requirements.txt" << EOF
tensorflow==2.20.0
EOF

echo "Installing TensorFlow (this may take a while)..."
pip install -r "${TENSORFLOW_DIR}/requirements.txt" \
    --target "${TENSORFLOW_DIR}/python/lib/python3.11/site-packages" \
    --no-deps --quiet

zip_layer "tensorflow-2.20.0"

# 3. XGBoost Layer
echo -e "\n${BLUE}3️⃣ Building XGBoost Layer${NC}"
XGBOOST_DIR=$(create_layer_structure "xgboost-3.0.4")

cat > "${XGBOOST_DIR}/requirements.txt" << EOF
xgboost==3.0.4
lightgbm==4.6.0
EOF

echo "Installing XGBoost and LightGBM..."
pip install -r "${XGBOOST_DIR}/requirements.txt" \
    --target "${XGBOOST_DIR}/python/lib/python3.11/site-packages" \
    --no-deps --quiet

zip_layer "xgboost-3.0.4"

# 4. API Dependencies Layer
echo -e "\n${BLUE}4️⃣ Building API Dependencies Layer${NC}"
API_DEPS_DIR=$(create_layer_structure "api-dependencies")

cat > "${API_DEPS_DIR}/requirements.txt" << EOF
fastapi==0.115.7
pydantic[email]==2.11.7
pydantic-settings==2.10.1
email-validator==2.2.0
PyJWT==2.10.1
python-jose[cryptography]==3.5.0
bcrypt==4.3.0
structlog==25.4.0
python-dotenv==1.1.1
typing-extensions==4.14.1
EOF

echo "Installing API dependencies..."
pip install -r "${API_DEPS_DIR}/requirements.txt" \
    --target "${API_DEPS_DIR}/python/lib/python3.11/site-packages" \
    --no-deps --quiet

zip_layer "api-dependencies"

# 5. Binance Client Layer
echo -e "\n${BLUE}5️⃣ Building Binance Client Layer${NC}"
BINANCE_DIR=$(create_layer_structure "binance-client")

cat > "${BINANCE_DIR}/requirements.txt" << EOF
aiohttp==3.12.15
websockets==15.0.1
requests==2.31.0
boto3==1.34.0
botocore==1.34.0
psutil==7.0.0
EOF

echo "Installing Binance client dependencies..."
pip install -r "${BINANCE_DIR}/requirements.txt" \
    --target "${BINANCE_DIR}/python/lib/python3.11/site-packages" \
    --no-deps --quiet

zip_layer "binance-client"

# 6. Trading Models Layer (placeholder)
echo -e "\n${BLUE}6️⃣ Building Trading Models Layer${NC}"
MODELS_DIR=$(create_layer_structure "trading-models-v1.0.0")

# Create placeholder model files
mkdir -p "${MODELS_DIR}/python/models"
cat > "${MODELS_DIR}/python/models/README.md" << EOF
# TradePulse.AI Trading Models

This layer contains pre-trained machine learning models for trading signal generation.

## Models included:
- LSTM 1-minute model
- LSTM 5-minute model  
- XGBoost ensemble model

## Usage:
Models are loaded from /opt/python/models/ in Lambda functions.
EOF

# Create placeholder model files
echo "Creating placeholder model files..."
touch "${MODELS_DIR}/python/models/lstm_1m_model.h5"
touch "${MODELS_DIR}/python/models/lstm_5m_model.h5"
touch "${MODELS_DIR}/python/models/xgb_ensemble_model.json"

zip_layer "trading-models-v1.0.0"

# Summary
echo -e "\n${GREEN}🎉 Lambda Layers Build Complete!${NC}"
echo "=================================================="
echo -e "${BLUE}Built layers:${NC}"
ls -la "${DIST_DIR}"

echo -e "\n${YELLOW}📋 Next Steps:${NC}"
echo "1. Upload layers to S3:"
echo "   aws s3 cp ${DIST_DIR}/ s3://your-layers-bucket/layers/ --recursive"
echo ""
echo "2. Deploy infrastructure:"
echo "   cd infra/terraform/envs/dev"
echo "   terraform apply"
echo ""
echo "3. Update Lambda functions to use these layers"

echo -e "\n${GREEN}✅ Build script completed successfully!${NC}"
