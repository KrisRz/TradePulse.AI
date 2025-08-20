# 🚀 TradePulse.AI Environment Setup Guide

**Complete setup guide for development and deployment environments**

---

## 📋 **PREREQUISITES**

### **System Requirements:**
- **macOS**: 10.15+ (Catalina or later)
- **Python**: 3.10+ (3.13 recommended)
- **Node.js**: 18+ (for frontend)
- **Java**: 17+ (for DynamoDB Local)
- **Git**: Latest version

### **Package Managers:**
- **Homebrew**: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- **pip**: Included with Python
- **npm**: Included with Node.js

---

## 🔧 **BACKEND SETUP**

### **1. Install System Dependencies**

```bash
# Install Python 3.13
brew install python@3.13

# Install Java 17 for DynamoDB Local
brew install openjdk@17

# Set Java environment (add to ~/.zshrc or ~/.bash_profile)
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
```

### **2. Backend Environment Setup**

```bash
# Navigate to backend directory
cd /Applications/Projects/TradePulse.AI/app/backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Run dependency installation script
./install_dependencies.sh
```

### **3. Verify Backend Setup**

```bash
# Test all imports
python -c "
from professional_trading_backend import app
print('✅ Backend imports successfully')
print('✅ All dependencies working')
"
```

### **4. Start Backend Services**

```bash
# Terminal 1: Start DynamoDB Local
cd data/dynamodb
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8000

# Terminal 2: Start Professional Backend
cd /Applications/Projects/TradePulse.AI/app/backend
source venv/bin/activate
uvicorn professional_trading_backend:app --host 0.0.0.0 --port 9001 --reload
```

---

## 🎨 **FRONTEND SETUP**

### **1. Install Node.js Dependencies**

```bash
# Navigate to frontend directory
cd /Applications/Projects/TradePulse.AI/app/frontend

# Install dependencies
npm install

# Verify installation
npm run build
```

### **2. Start Frontend Development Server**

```bash
# Start Astro development server
npm run dev
```

---

## 🗄️ **DATABASE SETUP**

### **1. DynamoDB Local Configuration**

```bash
# DynamoDB Local runs on port 8000
# Access via AWS SDK with:
# - endpoint: http://localhost:8000
# - region: us-east-1
# - accessKeyId: 'dummy'
# - secretAccessKey: 'dummy'
```

### **2. Required Tables**

The following tables are automatically created by the DatabaseService:

- `tradepulse-users` - User accounts
- `tradepulse-virtual-portfolios` - Virtual portfolios
- `tradepulse-signals` - Trading signals
- `tradepulse-positions` - Trading positions
- `tradepulse-analytics` - Analytics data
- `tradepulse-notifications` - Notifications
- `tradepulse-system-config` - System configuration

---

## 🔐 **ENVIRONMENT VARIABLES**

### **Backend Environment (.env)**

```bash
# Create .env file in backend directory
cd /Applications/Projects/TradePulse.AI/app/backend
cp .env.example .env

# Edit .env with your configuration
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here
BINANCE_API_KEY=your-binance-api-key
BINANCE_SECRET_KEY=your-binance-secret-key
DYNAMODB_ENDPOINT=http://localhost:8000
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
```

---

## 🚀 **DEPLOYMENT CHECKLIST**

### **✅ Development Environment**

- [ ] Python 3.13 installed
- [ ] Java 17 installed and configured
- [ ] Virtual environment created
- [ ] All dependencies installed via `install_dependencies.sh`
- [ ] Backend imports successfully
- [ ] DynamoDB Local running on port 8000
- [ ] Professional Backend running on port 9001
- [ ] Frontend development server running on port 4321
- [ ] All admin dashboard tabs loading with real data

### **✅ Production Environment**

- [ ] AWS account configured
- [ ] DynamoDB tables created in AWS
- [ ] Lambda functions deployed
- [ ] API Gateway configured
- [ ] CloudFront distribution set up
- [ ] S3 buckets created
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Domain configured
- [ ] Monitoring and logging set up

---

## 🛠️ **TROUBLESHOOTING**

### **Common Issues & Solutions**

#### **1. "No module named 'psutil'"**
```bash
source venv/bin/activate
pip install psutil==7.0.0
```

#### **2. "No module named 'jwt'"**
```bash
source venv/bin/activate
pip install PyJWT==2.10.1
```

#### **3. "No module named 'jose'"**
```bash
source venv/bin/activate
pip install 'python-jose[cryptography]==3.5.0'
```

#### **4. "email-validator is not installed"**
```bash
source venv/bin/activate
pip install 'pydantic[email]==2.11.7'
```

#### **5. "Unable to locate a Java Runtime"**
```bash
brew install openjdk@17
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
```

#### **6. "List is not defined"**
- All files now have proper typing imports
- Run `./install_dependencies.sh` to verify

#### **7. DynamoDB Local Connection Issues**
```bash
# Check if DynamoDB Local is running
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/x-amz-json-1.0" \
  -H "X-Amz-Target: DynamoDB_20120810.ListTables" \
  -d '{}'
```

---

## 📊 **SERVICE STATUS VERIFICATION**

### **Backend Health Check**
```bash
curl http://localhost:9001/health/health
# Expected: {"status":"operational","timestamp":"...","service":"TradePulse.AI Enterprise Backend"}
```

### **Admin Dashboard Endpoints**
```bash
# Portfolio Management
curl http://localhost:9001/api/portfolio/virtual/overview
# Expected: {"detail":"Not authenticated"} (correct - requires JWT)

# Analytics
curl http://localhost:9001/api/analytics/overview
# Expected: {"detail":"Not authenticated"} (correct - requires JWT)

# System Status
curl http://localhost:9001/api/admin/system/status
# Expected: {"detail":"Not authenticated"} (correct - requires JWT)
```

### **DynamoDB Local Health Check**
```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/x-amz-json-1.0" \
  -H "X-Amz-Target: DynamoDB_20120810.ListTables" \
  -d '{}'
# Expected: Authentication error (correct - DynamoDB is running)
```

---

## 🎯 **QUICK START COMMANDS**

### **Full Environment Startup**

```bash
#!/bin/bash
# Save as start_tradepulse.sh

# Set Java environment
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"

# Start DynamoDB Local
cd /Applications/Projects/TradePulse.AI/app/backend/data/dynamodb
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8000 &

# Start Backend
cd /Applications/Projects/TradePulse.AI/app/backend
source venv/bin/activate
uvicorn professional_trading_backend:app --host 0.0.0.0 --port 9001 --reload &

# Start Frontend
cd /Applications/Projects/TradePulse.AI/app/frontend
npm run dev &

echo "🚀 TradePulse.AI started successfully!"
echo "📊 Backend: http://localhost:9001"
echo "🎨 Frontend: http://localhost:4321"
echo "🗄️ DynamoDB Local: http://localhost:8000"
```

---

## 📈 **PERFORMANCE OPTIMIZATION**

### **Development Environment**
- Use `--reload` flag for auto-restart during development
- Enable debug mode in `.env`
- Use local DynamoDB for faster development

### **Production Environment**
- Disable debug mode
- Use AWS DynamoDB
- Enable CloudFront caching
- Configure auto-scaling
- Set up monitoring and alerts

---

## 🔒 **SECURITY CONSIDERATIONS**

### **Development**
- Use dummy AWS credentials for local DynamoDB
- Keep `.env` files out of version control
- Use HTTPS in production

### **Production**
- Use AWS IAM roles and policies
- Enable encryption at rest and in transit
- Implement proper authentication and authorization
- Regular security audits and updates

---

**Status**: ✅ **ENVIRONMENT FULLY CONFIGURED AND OPERATIONAL**

All dependency issues resolved, Java runtime configured, DynamoDB Local operational, and backend imports working perfectly. Ready for development and AWS deployment! 🚀
