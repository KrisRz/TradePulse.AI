# 🚀 TradePulse.AI - AWS Deployment Quick Start

## 🎯 Production Deployment: Local → AWS

### **Current Status**
- ✅ **Local Development**: Working with DynamoDB Local
- ✅ **AWS Infrastructure**: Terraform ready, cost-optimized ($47-92/month)
- ✅ **Singleton Safety**: LeaseGuard prevents double-trading during deploys
- ✅ **CI/CD Pipeline**: GitHub Actions with OIDC authentication

---

## 📊 Data Migration: DynamoDB Local → AWS DynamoDB

### **Migration Strategy (Recommended: Fresh Start)**

**✅ RECOMMENDED: Start Fresh in AWS**
```python
# AWS deployment creates empty DynamoDB tables
# Trading system handles empty state gracefully on startup
# Advantages:
# - Clean production environment
# - No data corruption risk
# - Professional deployment pattern
# - Faster deployment process
```

**Optional: Manual Migration (if needed)**
```python
# Only migrate essential data if absolutely necessary
# Portfolio state, key thresholds, learning parameters
# Script: app/backend/scripts/data/migrate_to_aws.py (create if needed)
```

### **Why Fresh Start is Better**
1. **Clean State**: Production starts with optimal configuration
2. **No Corruption**: Avoids potential data format issues
3. **Performance**: No legacy data affecting performance
4. **Professional**: Industry standard for production deployments

---

## 🚀 Step-by-Step AWS Deployment

### **Prerequisites Check**
```bash
# 1. AWS Account with admin permissions
# 2. GitHub repository with your code  
# 3. Binance API keys (live trading)
# 4. Domain (optional, for custom URL)

# Verify tools installed:
aws --version        # AWS CLI
terraform --version  # Terraform 1.5+
git --version       # Git
```

### **Step 1: Setup AWS Credentials**

**Option A: Use Existing Credentials (Quick)**
```bash
# Check if you have AWS credentials
aws sts get-caller-identity

# If working, proceed to Step 2
# If not, setup AWS CLI:
aws configure
# Enter: Access Key, Secret Key, Region (eu-central-1), Output (json)
```

**Option B: AWS SSO/Profile (Recommended)**
```bash
# If using AWS SSO or named profiles
aws configure sso
# Or use existing profile:
export AWS_PROFILE=your-profile-name
```

### **Step 2: Configure Infrastructure**
```bash
cd infra/

# Copy and edit configuration
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars - CRITICAL SETTINGS:
region = "eu-central-1"                    # Or your preferred region
project_name = "tradepulse"               # Keep consistent
environment = "prod"

# Your secrets:
binance_api_key = "your_real_binance_key"
binance_api_secret = "your_real_binance_secret"

# GitHub integration:
github_repo = "YourGitHubUsername/TradePulse.AI"
github_branch = "main"

# Cost optimization:
enable_vpc = false              # Saves $45/month (no NAT Gateway)
app_runner_min_size = 1        # Start minimal
app_runner_max_size = 2        # Conservative scaling
enable_monitoring = true       # Essential for production
```

### **Step 3: Deploy Infrastructure**
```bash
# Initialize Terraform
terraform init

# Preview changes  
terraform plan

# Deploy (creates OIDC provider, ECR, DynamoDB tables, etc.)
terraform apply

# IMPORTANT: Copy these outputs:
# - github_role_arn (for GitHub secrets)
# - ecr_repository_url (for verification)
# - app_runner_service_url (your production URL)
```

### **Step 4: Configure GitHub Secrets**
```bash
# Go to GitHub repository: Settings → Secrets and variables → Actions
# Add these 3 REQUIRED secrets:

AWS_ROLE_TO_ASSUME = "arn:aws:iam::123456789:role/tradepulse-github-actions-role"
BINANCE_API_KEY = "your_binance_api_key" 
BINANCE_API_SECRET = "your_binance_secret"

# Get AWS_ROLE_TO_ASSUME from terraform output:
terraform output github_role_arn
```

### **Step 5: Deploy to Production**
```bash
# Trigger deployment by pushing to main
git add .
git commit -m "Initial AWS production deployment"
git push origin main

# GitHub Actions will:
# ✅ Build Docker image
# ✅ Push to ECR
# ✅ Deploy infrastructure updates  
# ✅ Start App Runner service
# ✅ Run health checks
# ✅ Send notifications

# Monitor deployment:
# GitHub: Actions tab → Watch workflow progress
# AWS Console: App Runner → tradepulse-backend service
```

### **Step 6: Verify Deployment**
```bash
# Get your production URL
terraform output app_runner_service_url
# Example: https://abc123.eu-central-1.awsapprunner.com

# Test endpoints:
curl https://your-url/health                    # Should return {"status": "healthy"}
curl https://your-url/ready                     # Should return {"ready": true} 
curl https://your-url/api/v1/trading/brain/status  # Trading brain status

# Check trading brain is running:
# Should see: "is_leader": true, "lease_owner": "your-instance-id"
```

---

## 🏥 Production Health Monitoring

### **Key Health Checks**
```bash
# App Runner health
aws apprunner describe-service --service-arn $(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='tradepulse-backend'].ServiceArn" --output text)

# DynamoDB tables
aws dynamodb list-tables --query "TableNames[?starts_with(@, 'tradepulse_')]"

# Check logs for trading activity
aws logs filter-log-events \
  --log-group-name /aws/apprunner/tradepulse-backend \
  --filter-pattern "trading_brain_loop OR Acquired trading brain lease"
```

### **CloudWatch Dashboard**
- **URL**: AWS Console → CloudWatch → Dashboards → tradepulse-prod
- **Metrics**: App Runner requests, DynamoDB usage, custom trading metrics
- **Alarms**: High response time, DynamoDB throttling, missing heartbeat
- **Notifications**: Alarms visible in CloudWatch console (no SNS for cost optimization)

### **Cost Monitoring**
```bash
# Setup billing alerts in AWS Console
# Billing → Budgets → Create budget
# Alert thresholds: $50 (warning), $75 (concern), $100 (action required)

# Check current costs:
aws budgets describe-budgets --account-id $(aws sts get-caller-identity --query Account --output text)
```

---

## 🔧 Troubleshooting Common Issues

### **1. GitHub Actions Deployment Fails**
```bash
# Check GitHub Actions logs
# Common issues:
# - Wrong AWS_ROLE_TO_ASSUME ARN
# - Missing Binance API keys
# - Terraform state conflicts

# Fix Terraform state:
cd infra/
terraform refresh
terraform plan
```

### **2. App Runner Service Won't Start**
```bash
# Check App Runner logs
aws logs tail /aws/apprunner/tradepulse-backend --follow

# Common issues:
# - Container build failures
# - Missing environment variables
# - Health check failures
```

### **3. Trading Brain Not Starting**
```bash
# Check for lease acquisition issues
aws logs filter-log-events \
  --log-group-name /aws/apprunner/tradepulse-backend \
  --filter-pattern "LeaseGuard OR Acquired trading brain lease"

# Check DynamoDB runtime table
aws dynamodb scan --table-name tradepulse_runtime
```

### **4. High AWS Costs**
```bash
# Check cost breakdown
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE

# Common cost culprits:
# - Multiple App Runner instances running (should be 1-2)  
# - High DynamoDB usage (check for scan operations)
# - Excessive CloudWatch log ingestion
```

---

## 📊 Production vs Development

| Feature | Local Development | AWS Production |
|---------|-------------------|----------------|
| **Database** | DynamoDB Local (file) | DynamoDB Managed |
| **Trading Brain** | Single instance | Singleton with lease |
| **Scaling** | Manual | Auto (1-3 instances) |
| **Monitoring** | Logs only | CloudWatch + SNS |
| **Secrets** | .env files | SSM Parameter Store |
| **SSL** | HTTP | Auto HTTPS |
| **Cost** | $0 | $47-92/month |
| **Reliability** | Dev only | Production grade |
| **Data Migration** | N/A | Fresh start recommended |

---

## 🎯 Next Steps After Deployment

### **Immediate (Day 1)**
- [ ] Verify all health endpoints respond correctly
- [ ] Confirm trading brain acquired lease and is running
- [ ] Check CloudWatch logs for any errors
- [ ] Setup cost alerts and monitoring

### **First Week**
- [ ] Monitor trading performance and accuracy
- [ ] Review cost usage patterns
- [ ] Fine-tune auto-scaling thresholds if needed
- [ ] Setup custom domain (optional)

### **First Month** 
- [ ] Analyze trading results and optimize parameters
- [ ] Consider enabling VPC if security requirements change
- [ ] Scale instance size if performance bottlenecks detected
- [ ] Plan real money integration (replace demo trading)

---

## 💰 Cost Optimization Tips

### **Keep Costs Low**
1. **Leave VPC disabled** (saves $45/month NAT Gateway)
2. **Start with 1 vCPU/2GB** App Runner instance
3. **Monitor DynamoDB usage** - optimize query patterns
4. **Reduce log retention** to 7-14 days
5. **Use billing alerts** to catch spikes early

### **Scale When Profitable**
- **$200/month revenue**: Upgrade to 2 vCPU/4GB
- **$500/month revenue**: Add VPC, custom domain  
- **$1000/month revenue**: Multi-AZ, reserved instances

---

**🎉 Your TradePulse.AI system is now running on AWS with professional infrastructure!**

**Production URL**: Check `terraform output app_runner_service_url`
**Trading Status**: `https://your-url/api/v1/trading/brain/status`
**Admin Dashboard**: `https://your-url/admin/dashboard` (when frontend deployed)

**Total deployment time: ~15-30 minutes from start to finish!** 🚀
