# TradePulse.AI - AWS Deployment Guide

## Architecture Overview

**Production Architecture:**
- **App Runner** - Zarządzany backend z auto-scaling (1-3 instances)
- **DynamoDB** - Managed NoSQL database z on-demand billing
- **ECR** - Container registry dla Docker images
- **SSM Parameter Store** - Secure configuration management  
- **CloudWatch** - Monitoring, logs, i alerty
- **VPC** (opcjonalne) - Private networking z DynamoDB VPC Endpoint

## 🚀 Quick Start Deployment

### Prerequisites

1. **AWS Account** z odpowiednimi uprawnieniami
2. **GitHub repository** z kodem
3. **Binance API Keys** (Professional Live Trading)
4. **Terraform** >= 1.5 installed locally (opcjonalnie)

### Step 1: Setup GitHub OIDC

```bash
# 1. Create AWS OIDC Identity Provider (jednorazowo)
# To zostanie zrobione przez Terraform automatycznie

# 2. Configure GitHub Secrets
# W GitHub repo -> Settings -> Secrets and variables -> Actions

# Required secrets:
AWS_ROLE_TO_ASSUME=arn:aws:iam::YOUR_ACCOUNT:role/tradepulse-github-actions-role
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_secret
```

### Step 2: Configure Terraform Variables

```bash
cd infra/
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values:
region = "eu-central-1"
binance_api_key = "your-key-here"
binance_api_secret = "your-secret-here"
github_repo = "YourUsername/TradePulse.AI"
```

### Step 3: Manual Terraform Bootstrap (One-time)

```bash
# Initialize and deploy infrastructure
terraform init
terraform plan
terraform apply

# Note: First deployment creates OIDC provider
# After this, GitHub Actions will handle deployments
```

### Step 4: Trigger Deployment

```bash
# Push to main branch triggers full deployment
git add .
git commit -m "Deploy to AWS production"
git push origin main

# GitHub Actions will:
# 1. Build Docker image
# 2. Push to ECR  
# 3. Deploy infrastructure
# 4. Update App Runner service
# 5. Verify health checks
```

## 🔧 Configuration

### Environment Variables (Auto-configured)

App Runner zostanie skonfigurowany z następującymi zmiennymi:

```bash
# Production Environment
ENV=production
AWS_REGION=eu-central-1
DYNAMODB_TABLE_PREFIX=tradepulse_

# Trading Configuration  
PROFESSIONAL_MODE=true
STRICT_LIVE_STREAM=true
TRADING_SYMBOL=BTCUSDT
TRADING_MODE=DAY_TRADING

# Secrets (from SSM Parameter Store)
BINANCE_API_KEY=${ssm:/tradepulse/prod/BINANCE_API_KEY}
BINANCE_API_SECRET=${ssm:/tradepulse/prod/BINANCE_API_SECRET}
```

### DynamoDB Tables

Automatycznie tworzone tabele:
- `tradepulse_signals` - Trading signals z AI analysis
- `tradepulse_portfolio` - Portfolio state i positions  
- `tradepulse_positions` - Active trading positions
- `tradepulse_analytics` - Market analytics i performance  
- `tradepulse_brain_state` - Brain Controller FSM state
- `tradepulse_market_data` - Live market data cache

## 🏥 Health Monitoring

### App Runner Health Checks
- **Path:** `/health`
- **Interval:** 10s
- **Timeout:** 5s
- **Healthy threshold:** 1
- **Unhealthy threshold:** 3

### CloudWatch Monitoring

**Automatic Dashboards:**
- App Runner metrics (latency, errors, instances)
- DynamoDB metrics (throttling, capacity)
- Custom metrics (signals generated, errors, WebSocket reconnections)

**Alarms:**
- High response time (>5s)
- High error rate (>10 4xx responses)
- DynamoDB throttling

### Key Metrics

```bash
# Trading Brain Status
curl https://your-service.app-runner.amazonaws.com/api/v1/trading/brain/status

# Health Check  
curl https://your-service.app-runner.amazonaws.com/health

# AI Models Status
curl https://your-service.app-runner.amazonaws.com/api/v1/signals/ai-models-status
```

## 🚨 Troubleshooting

### Common Issues

**1. App Runner Deployment Failed**
```bash
# Check CloudWatch logs
aws logs tail /aws/apprunner/tradepulse-backend --follow

# Check service status
aws apprunner describe-service --service-arn $(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='tradepulse-backend'].ServiceArn" --output text)
```

**2. Trading Brain Not Starting**
```bash
# Check logs for WebSocket connection issues
aws logs filter-log-events \
  --log-group-name /aws/apprunner/tradepulse-backend \
  --filter-pattern "WebSocket OR Brain Controller OR trading_brain_loop"
```

**3. DynamoDB Connection Issues**
```bash
# Verify DynamoDB tables exist
aws dynamodb list-tables --query "TableNames[?starts_with(@, 'tradepulse_')]"

# Check table status
aws dynamodb describe-table --table-name tradepulse_signals --query "Table.TableStatus"
```

**4. Missing Binance Data**
```bash
# Check API key configuration
aws ssm get-parameter --name "/tradepulse/prod/BINANCE_API_KEY" --with-decryption

# Look for API errors in logs
aws logs filter-log-events \
  --log-group-name /aws/apprunner/tradepulse-backend \
  --filter-pattern "Binance OR API"
```

## 🔐 Security Best Practices

### Implemented Security Measures

1. **Non-root container** - App runs as `tradepulse` user
2. **Secrets management** - API keys in SSM Parameter Store  
3. **VPC networking** (optional) - Private subnets + NAT Gateway
4. **IAM least privilege** - Specific permissions per service
5. **Container scanning** - Trivy security scans in CI/CD
6. **HTTPS only** - App Runner provides automatic SSL

### Security Checklist

- [ ] Binance API keys rotated regularly
- [ ] CloudWatch log retention configured (14 days)
- [ ] SSM parameters encrypted with KMS  
- [ ] App Runner instances in private subnets (if VPC enabled)
- [ ] Security group rules minimized
- [ ] Container images scanned for vulnerabilities

## 💰 Cost Optimization

### Expected Monthly Costs (eu-central-1)

**App Runner:**
- 1 instance, 1 vCPU, 2GB RAM: ~$25-40/month
- Auto-scaling to 3 instances under load: ~$75-120/month

**DynamoDB:**
- On-demand billing: $1.25 per million writes, $0.25 per million reads
- Estimated: $10-50/month for active trading

**Other Services:**
- ECR storage: ~$1-5/month  
- CloudWatch logs: ~$5-15/month
- VPC (optional): NAT Gateway ~$45/month

**Total estimated:** $50-200/month depending on trading volume

### Cost Optimization Tips

1. **Disable VPC** if private networking not required (saves $45/month)
2. **Adjust log retention** - 3-7 days instead of 14
3. **Monitor DynamoDB usage** - optimize query patterns
4. **Use CloudWatch billing alarms** for budget control

## 📊 Performance Tuning

### App Runner Configuration

```hcl
# Current settings (adjust in terraform.tfvars)
app_runner_cpu = "1024"    # 1 vCPU - sufficient for current load
app_runner_memory = "2048" # 2 GB - handles ML models + WebSocket
app_runner_min_size = 1    # Always 1 instance running
app_runner_max_size = 3    # Scale up during high activity
```

### Performance Benchmarks

**Expected Performance:**
- Trading signal generation: ~500-2000ms
- WebSocket message processing: <100ms
- Health check response: <200ms
- Background brain loop: 15s cycles

**Scaling Triggers:**
- CPU utilization >70%
- Request queue depth >10
- Response time >3s

## 🔄 Maintenance & Updates

### Automated Updates

**GitHub Actions handles:**
- Code changes → automatic Docker build + deploy
- Infrastructure changes → Terraform apply
- Health checks → rollback on failure

### Manual Maintenance

```bash
# Check service health
aws apprunner describe-service --service-arn YOUR_SERVICE_ARN

# View recent deployments  
aws apprunner list-operations --service-arn YOUR_SERVICE_ARN

# Manual rollback (if needed)
aws apprunner start-deployment --service-arn YOUR_SERVICE_ARN

# Database maintenance
aws dynamodb describe-table --table-name tradepulse_signals
```

### Backup Strategy

**Automated Backups:**
- DynamoDB Point-in-Time Recovery: enabled (up to 35 days)
- ECR image lifecycle: keeps 20 most recent images
- CloudWatch logs: 14-day retention

## 🌐 Custom Domain (Optional)

```hcl
# In terraform.tfvars
custom_domain = "api.tradepulse.ai"
hosted_zone_id = "Z1D633PJN98FT9"  # Your Route53 hosted zone
```

App Runner automatically provides:
- SSL certificate (AWS Certificate Manager)
- CNAME validation via Route53
- Automatic certificate renewal

---

## 📞 Support

For deployment issues:
1. Check CloudWatch logs first
2. Review GitHub Actions workflow logs  
3. Verify AWS service quotas
4. Check this troubleshooting guide

**Production URL:** https://your-service-id.eu-central-1.awsapprunner.com
**Health endpoint:** https://your-service-id.eu-central-1.awsapprunner.com/health
