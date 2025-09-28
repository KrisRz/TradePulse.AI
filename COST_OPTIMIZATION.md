# TradePulse.AI - Cost Optimization Guide 💰

## Current Architecture - Minimal Viable Production

### 🏗️ Services Used (Cost-Optimized)
- **App Runner**: 1 vCPU, 2GB RAM (minimal size)
- **DynamoDB**: On-demand billing (no reserved capacity)
- **ECR**: Basic container registry
- **SSM Parameter Store**: Free tier (< 10,000 parameters)
- **CloudWatch**: Basic monitoring + logs (alarms without SNS)
- **No VPC/NAT Gateway**: Saves $45/month

### 💰 Monthly Cost Breakdown (eu-central-1)

**App Runner - 24/7 Operation**
- 1 instance: 1 vCPU, 2GB RAM
- Base cost: ~$25-35/month
- Auto-scaling (max 3): Only pay when used
- Estimated: **$30-50/month**

**DynamoDB - On-Demand**
- Write requests: $1.25 per million
- Read requests: $0.25 per million  
- Storage: $0.25/GB/month
- Estimated for trading app: **$10-30/month**

**Other Services**
- ECR storage: $0.10/GB/month (~$2/month)
- CloudWatch logs: $0.50/GB (~$5-10/month)
- SSM Parameter Store: Free tier
- **Total other: ~$7-12/month**

### 🎯 **Total Estimated Cost: $47-92/month**

## 📊 Cost Monitoring & Alarms

### Setup Billing Alarms

```bash
# Add to terraform.tfvars
billing_alert_threshold = 100  # $100/month alert
```

### Key Cost Metrics to Monitor

1. **App Runner Instance Hours**
   - Target: 744 hours/month (24/7 single instance)
   - Alert if > 1500 hours (multiple instances running)

2. **DynamoDB Requests**
   - Monitor read/write capacity consumption
   - Alert if > 10M requests/month

3. **CloudWatch Log Data**
   - Monitor log ingestion volume
   - Reduce log retention if needed

## 🔧 Further Cost Optimizations

### Phase 1: Current (Minimal Viable)
```hcl
# Current settings in terraform.tfvars
app_runner_cpu = "1024"    # 1 vCPU
app_runner_memory = "2048" # 2 GB  
app_runner_min_size = 1    # Always 1 instance
app_runner_max_size = 2    # Scale to max 2 (was 3)
enable_vpc = false         # No VPC = no NAT Gateway cost
```

### Phase 2: Revenue-Based Scaling

**When app generates $200+/month:**
- Increase to 2 vCPU/4GB for better ML performance
- Add custom domain + SSL
- Enable VPC for better security

**When app generates $500+/month:**
- Add ALB + ECS for more control
- Add RDS for relational data
- Multi-AZ deployment

### Phase 3: High Revenue Optimizations

**When app generates $1000+/month:**
- Reserved Instance pricing
- Multi-region deployment  
- Dedicated Tenancy for compliance

## ⚡ Performance vs Cost Balance

### Current Configuration Handles:
- **WebSocket connections**: 50-100 concurrent
- **API requests**: 1000 requests/minute
- **ML model inference**: 2-5 second latency
- **Trading signals**: 15-second generation cycle

### Scaling Triggers:
- **CPU > 70%** for 5 minutes → scale to 2 instances
- **Memory > 80%** → consider upgrading instance size
- **Response time > 5s** → investigate bottlenecks

## 🚨 Cost Alerts & Actions

### Automated Cost Controls

1. **$50 Alert** - Normal usage
2. **$75 Alert** - Check for scaling events  
3. **$100 Limit** - Investigation required

### Emergency Cost Control

```bash
# If costs spike unexpectedly:

# 1. Scale down App Runner
aws apprunner update-service --service-arn YOUR_ARN \
  --auto-scaling-configuration-arn YOUR_CONFIG_ARN

# 2. Check DynamoDB usage
aws dynamodb describe-table --table-name tradepulse_signals \
  --query "Table.BillingModeSummary"

# 3. Review CloudWatch log retention
aws logs describe-log-groups --log-group-name-prefix "/aws/apprunner"
```

## 📈 ROI Calculation

### Break-Even Analysis
- **Fixed costs**: ~$50-75/month
- **Variable costs**: Scale with usage
- **Target**: Break-even at $100 revenue/month
- **Profit margin**: 25-50% after break-even

### Cost Per Trade
- **Successful trade profit**: $10-50
- **Infrastructure cost per trade**: ~$0.10-0.50
- **Net profit margin**: 90-98% per trade

## 🔄 Monthly Cost Review Checklist

- [ ] Review App Runner instance hours
- [ ] Check DynamoDB request patterns
- [ ] Analyze CloudWatch log volume
- [ ] Monitor auto-scaling events
- [ ] Review unused resources
- [ ] Optimize DynamoDB indexes
- [ ] Clean up old ECR images (automated)

## 💡 Cost Optimization Tips

### DynamoDB
- Use TTL for automatic cleanup
- Optimize query patterns to reduce scans
- Monitor hot partitions
- Use batch operations when possible

### App Runner  
- Optimize container image size
- Use health checks efficiently
- Monitor cold start times
- Set appropriate auto-scaling thresholds

### CloudWatch
- Set appropriate log retention (7-14 days)
- Use log filters to reduce noise
- Monitor metric filters usage

---

## 🎯 Next Steps

1. **Deploy with current minimal config**
2. **Monitor costs for 1-2 months**  
3. **Optimize based on actual usage patterns**
4. **Scale up only when revenue justifies it**

**Remember**: Start small, monitor closely, scale strategically. The goal is profitable trading, not perfect infrastructure! 🚀
