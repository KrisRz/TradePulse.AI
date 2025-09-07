#!/bin/bash

# TradePulse.AI - Infrastructure Deployment Script
# Deploys enhanced serverless infrastructure to AWS

set -e  # Exit on any error

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TERRAFORM_DIR="${PROJECT_ROOT}/infra/terraform"
ENV="${1:-dev}"  # Default to dev environment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 TradePulse.AI - Infrastructure Deployment${NC}"
echo "=============================================="
echo -e "${YELLOW}Environment: ${ENV}${NC}"
echo -e "${YELLOW}Terraform Dir: ${TERRAFORM_DIR}${NC}"

# Validate environment
if [[ ! "$ENV" =~ ^(dev|prod)$ ]]; then
    echo -e "${RED}❌ Invalid environment: $ENV${NC}"
    echo "Usage: $0 [dev|prod]"
    exit 1
fi

# Check if terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform is not installed${NC}"
    exit 1
fi

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "eu-west-2")

echo -e "${GREEN}✅ AWS Account: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${GREEN}✅ AWS Region: ${AWS_REGION}${NC}"

# Function to run terraform commands
run_terraform() {
    local action=$1
    local dir=$2
    local extra_args="${3:-}"
    
    echo -e "\n${BLUE}🔧 Running terraform ${action} in ${dir}${NC}"
    cd "${dir}"
    
    case $action in
        "init")
            terraform init
            ;;
        "plan")
            terraform plan ${extra_args}
            ;;
        "apply")
            terraform apply ${extra_args}
            ;;
        "destroy")
            terraform destroy ${extra_args}
            ;;
    esac
    
    cd "${PROJECT_ROOT}"
}

# Step 1: Bootstrap (if not already done)
echo -e "\n${YELLOW}📋 Step 1: Checking Bootstrap State${NC}"
BOOTSTRAP_DIR="${TERRAFORM_DIR}/global/bootstrap"

if [[ ! -f "${BOOTSTRAP_DIR}/.terraform/terraform.tfstate" ]]; then
    echo -e "${YELLOW}🔄 Bootstrap not initialized, running bootstrap...${NC}"
    
    # Create unique bucket name
    BUCKET_NAME="tradepulse-tfstate-${AWS_ACCOUNT_ID}-${AWS_REGION}"
    
    run_terraform "init" "${BOOTSTRAP_DIR}"
    run_terraform "apply" "${BOOTSTRAP_DIR}" "-var=\"tfstate_bucket_name=${BUCKET_NAME}\" -auto-approve"
    
    echo -e "${GREEN}✅ Bootstrap completed${NC}"
else
    echo -e "${GREEN}✅ Bootstrap already initialized${NC}"
fi

# Step 2: Deploy Environment Infrastructure
echo -e "\n${YELLOW}📋 Step 2: Deploying ${ENV} Environment${NC}"
ENV_DIR="${TERRAFORM_DIR}/envs/${ENV}"

if [[ ! -d "${ENV_DIR}" ]]; then
    echo -e "${RED}❌ Environment directory not found: ${ENV_DIR}${NC}"
    exit 1
fi

# Check if terraform.tfvars exists
if [[ ! -f "${ENV_DIR}/terraform.tfvars" ]]; then
    echo -e "${YELLOW}⚠️ terraform.tfvars not found, copying from example...${NC}"
    cp "${ENV_DIR}/terraform.tfvars.example" "${ENV_DIR}/terraform.tfvars"
    
    echo -e "${YELLOW}📝 Please edit ${ENV_DIR}/terraform.tfvars with your values${NC}"
    echo -e "${YELLOW}Especially set your secret values (API keys, etc.)${NC}"
    
    read -p "Press Enter to continue after editing terraform.tfvars..."
fi

# Initialize and plan
run_terraform "init" "${ENV_DIR}"
run_terraform "plan" "${ENV_DIR}" "-out=tfplan"

# Confirm deployment
echo -e "\n${YELLOW}🤔 Ready to deploy ${ENV} environment?${NC}"
echo -e "${YELLOW}This will create AWS resources that may incur costs.${NC}"
read -p "Continue? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    run_terraform "apply" "${ENV_DIR}" "tfplan"
    
    echo -e "\n${GREEN}🎉 Infrastructure Deployment Complete!${NC}"
    echo "=============================================="
    
    # Display outputs
    echo -e "\n${BLUE}📊 Infrastructure Outputs:${NC}"
    cd "${ENV_DIR}"
    terraform output
    cd "${PROJECT_ROOT}"
    
    # Next steps
    echo -e "\n${YELLOW}📋 Next Steps:${NC}"
    echo "1. Build and upload Lambda layers:"
    echo "   ./scripts/build-lambda-layers.sh"
    echo ""
    echo "2. Upload layers to S3:"
    echo "   aws s3 cp dist/layers/ s3://\$(terraform -chdir=${ENV_DIR} output -raw layers_bucket)/layers/ --recursive"
    echo ""
    echo "3. Build and deploy Lambda functions:"
    echo "   ./scripts/build-lambda-functions.sh ${ENV}"
    echo ""
    echo "4. Deploy frontend:"
    echo "   ./scripts/deploy-frontend.sh ${ENV}"
    
else
    echo -e "${YELLOW}⏸️ Deployment cancelled${NC}"
fi

echo -e "\n${GREEN}✅ Deployment script completed!${NC}"
