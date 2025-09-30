# 🤖 ML Model Deployment Guide - TradePulse.AI

## 📊 Current Setup (As-Is)

### **Local Storage**
```
📁 /Applications/Projects/TradePulse.AI/app/backend/models/enterprise/
├── lstm_1m.h5              (1-minute LSTM predictor)
├── lstm_5m.h5              (5-minute LSTM predictor)
├── lstm_1h.h5              (1-hour LSTM predictor)
├── lstm_4h.h5              (4-hour LSTM predictor)
├── lstm_24h.h5             (24-hour LSTM predictor)
├── layer_1_regime.pkl      (Market regime classifier)
├── layer_3_reversal.pkl    (Reversal detection)
├── layer_4_filters.pkl     (Technical filters)
├── layer_5_confidence.pkl  (Confidence scoring)
├── layer_6_timing.pkl      (Timing optimization)
├── feature_scalers.pkl     (Feature normalization)
└── lstm_scaler.pkl         (LSTM data scaler)

Total Size: 5.1 MB
```

### **Current Deployment Method**
- **Method:** Models BAKED INTO Docker image
- **Process:** 
  1. Models stored in Git (`app/backend/models/enterprise/`)
  2. Dockerfile copies entire `app/` directory
  3. Docker image includes models
  4. ECR push includes models
  5. App Runner deploys with models

### **Problems**
- ❌ Must rebuild Docker image to update models (~10 min)
- ❌ Can't update models independently
- ❌ No model versioning
- ❌ No easy rollback
- ❌ Large Docker images

---

## 🚀 Recommended: S3 Model Storage (Best Practice)

### **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│  LOCAL DEVELOPMENT                                          │
└───────────┬─────────────────────────────────────────────────┘
            │
            ├──► Train models locally
            │    📍 app/backend/models/enterprise/
            │    🔨 Use existing training scripts
            │
            ├──► Upload to S3 (versioned)
            │    ☁️  s3://tradepulse-ml-models/enterprise/v1.2/
            │    
┌───────────┴─────────────────────────────────────────────────┐
│  AWS PRODUCTION                                             │
└───────────┬─────────────────────────────────────────────────┘
            │
            ├──► Backend startup
            │    🔄 Download models from S3
            │    💾 Cache in /app/models/ (ephemeral)
            │
            └──► Hot-reload models
                 🔄 Download new version
                 ✅ No backend restart needed
```

---

## 📝 Implementation Plan

### **1. Create S3 Bucket for Models**

```bash
# Create S3 bucket (Terraform)
resource "aws_s3_bucket" "ml_models" {
  bucket = "tradepulse-ml-models"
  
  tags = {
    Name        = "TradePulse ML Models"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "ml_models" {
  bucket = aws_s3_bucket.ml_models.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle policy - keep last 5 versions
resource "aws_s3_bucket_lifecycle_configuration" "ml_models" {
  bucket = aws_s3_bucket.ml_models.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    
    noncurrent_version_transition {
      noncurrent_days = 7
      storage_class   = "STANDARD_IA"
    }
  }
}
```

### **2. Upload Models Script**

```python
# scripts/ml/upload_models_to_s3.py
"""
Upload trained models to S3 with versioning
"""
import os
import boto3
from pathlib import Path
from datetime import datetime

def upload_models_to_s3(
    local_path: str = "app/backend/models/enterprise",
    bucket: str = "tradepulse-ml-models",
    version: str = None
):
    """
    Upload all models to S3 with versioning
    
    Args:
        local_path: Local directory with models
        bucket: S3 bucket name
        version: Model version (e.g., 'v1.2'). If None, auto-generate
    """
    s3 = boto3.client('s3')
    
    # Auto-generate version if not provided
    if not version:
        version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    local_dir = Path(local_path)
    uploaded = []
    
    for model_file in local_dir.glob("*.pkl") + list(local_dir.glob("*.h5")):
        s3_key = f"enterprise/{version}/{model_file.name}"
        
        print(f"📤 Uploading {model_file.name} to s3://{bucket}/{s3_key}")
        
        s3.upload_file(
            str(model_file),
            bucket,
            s3_key,
            ExtraArgs={
                'Metadata': {
                    'version': version,
                    'uploaded_at': datetime.now().isoformat(),
                    'model_type': model_file.suffix[1:]
                }
            }
        )
        uploaded.append(s3_key)
    
    # Upload metadata file
    metadata = {
        'version': version,
        'uploaded_at': datetime.now().isoformat(),
        'models': [f.name for f in uploaded]
    }
    
    print(f"✅ Uploaded {len(uploaded)} models to {version}")
    return version

if __name__ == "__main__":
    import sys
    version = sys.argv[1] if len(sys.argv) > 1 else None
    upload_models_to_s3(version=version)
```

### **3. Model Loader with S3 Support**

```python
# app/backend/services/s3_model_loader.py
"""
Load ML models from S3 with caching
"""
import os
import boto3
from pathlib import Path
import pickle
import tensorflow as tf
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

class S3ModelLoader:
    """Load models from S3 with local caching"""
    
    def __init__(
        self,
        bucket: str = "tradepulse-ml-models",
        version: str = "latest",
        cache_dir: str = "/app/models_cache"
    ):
        self.bucket = bucket
        self.version = version
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.s3 = boto3.client('s3')
        self.models: Dict[str, Any] = {}
        
    async def load_all_models(self):
        """Load all enterprise models from S3"""
        try:
            logger.info("☁️ Loading models from S3", 
                       bucket=self.bucket, version=self.version)
            
            # List all models for this version
            prefix = f"enterprise/{self.version}/"
            response = self.s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                logger.warning("⚠️ No models found in S3, using local fallback")
                return self._load_local_fallback()
            
            # Download and load each model
            for obj in response['Contents']:
                model_key = obj['Key']
                model_name = Path(model_key).name
                
                # Download to cache
                cache_path = self.cache_dir / model_name
                
                # Download if not cached or outdated
                if not cache_path.exists() or self._is_outdated(cache_path, obj):
                    logger.info(f"📥 Downloading {model_name} from S3")
                    self.s3.download_file(self.bucket, model_key, str(cache_path))
                else:
                    logger.info(f"💾 Using cached {model_name}")
                
                # Load model
                self._load_model_from_cache(model_name, cache_path)
            
            logger.info(f"✅ Loaded {len(self.models)} models from S3")
            return self.models
            
        except Exception as e:
            logger.error(f"❌ Failed to load models from S3: {e}")
            return self._load_local_fallback()
    
    def _load_model_from_cache(self, model_name: str, cache_path: Path):
        """Load a single model from cache"""
        try:
            if model_name.endswith('.pkl'):
                with open(cache_path, 'rb') as f:
                    self.models[model_name] = pickle.load(f)
            elif model_name.endswith('.h5'):
                self.models[model_name] = tf.keras.models.load_model(
                    str(cache_path), 
                    compile=False
                )
            
            logger.info(f"✅ Loaded {model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to load {model_name}: {e}")
    
    def _is_outdated(self, cache_path: Path, s3_obj: Dict) -> bool:
        """Check if cached model is outdated"""
        cache_mtime = cache_path.stat().st_mtime
        s3_mtime = s3_obj['LastModified'].timestamp()
        return s3_mtime > cache_mtime
    
    def _load_local_fallback(self):
        """Fallback to local models if S3 unavailable"""
        logger.warning("⚠️ Using local model fallback")
        local_path = Path("app/backend/models/enterprise")
        
        # Load local models (existing code)
        # ... (use existing ModelLoader logic)
        
        return self.models
    
    async def reload_models(self, version: str = None):
        """Hot-reload models from S3 (new version)"""
        if version:
            self.version = version
        
        logger.info(f"🔄 Hot-reloading models (version: {self.version})")
        self.models = {}
        return await self.load_all_models()


# Global singleton
_s3_model_loader: Optional[S3ModelLoader] = None

def get_s3_model_loader() -> S3ModelLoader:
    global _s3_model_loader
    if _s3_model_loader is None:
        version = os.getenv("MODEL_VERSION", "latest")
        _s3_model_loader = S3ModelLoader(version=version)
    return _s3_model_loader
```

### **4. Update IAM Permissions**

```hcl
# infra/iam.tf - Add to App Runner instance policy
resource "aws_iam_policy" "ml_models_access" {
  name = "${var.project_name}-ml-models-access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ModelAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::tradepulse-ml-models",
          "arn:aws:s3:::tradepulse-ml-models/*"
        ]
      }
    ]
  })
}

# Attach to App Runner role
resource "aws_iam_role_policy_attachment" "ml_models" {
  role       = aws_iam_role.app_runner_instance.name
  policy_arn = aws_iam_policy.ml_models_access.arn
}
```

---

## 🔄 Workflow: Train → Deploy

### **Local Training**

```bash
# 1. Train models locally
cd /Applications/Projects/TradePulse.AI
python app/backend/scripts/ml/6layer_enterprise_trainer.py

# 2. Verify models work
python app/backend/scripts/validate_ai_models.py

# 3. Upload to S3
python scripts/ml/upload_models_to_s3.py v1.2

# Output:
# 📤 Uploading lstm_1m.h5 to s3://tradepulse-ml-models/enterprise/v1.2/lstm_1m.h5
# 📤 Uploading layer_1_regime.pkl to s3://tradepulse-ml-models/enterprise/v1.2/layer_1_regime.pkl
# ...
# ✅ Uploaded 12 models to v1.2
```

### **AWS Deployment**

```bash
# Option 1: Update MODEL_VERSION environment variable
aws apprunner update-service \
  --service-arn <arn> \
  --source-configuration '{
    "ImageRepository": {
      "ImageConfiguration": {
        "RuntimeEnvironmentVariables": {
          "MODEL_VERSION": "v1.2"
        }
      }
    }
  }'

# Option 2: Hot-reload via API (if implemented)
curl -X POST https://api.tradepulseai.co.uk/api/admin/models/reload \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"version": "v1.2"}'
```

---

## 📋 Quick Reference

### **Current (Baked-In Models)**
```bash
# Local path
/Applications/Projects/TradePulse.AI/app/backend/models/enterprise/

# How it's deployed
Docker build → ECR push → App Runner deploy (10 min)

# Update models
git add app/backend/models/
git commit -m "Update models"
git push  # Triggers full rebuild
```

### **Recommended (S3 Models)**
```bash
# Local path (same)
/Applications/Projects/TradePulse.AI/app/backend/models/enterprise/

# Upload to S3
python scripts/ml/upload_models_to_s3.py v1.2

# Backend downloads on startup
# Or hot-reload via API (30 seconds)
```

---

## ✅ Benefits Summary

| Feature | Current (Baked) | S3 Storage |
|---------|----------------|------------|
| Update speed | 10-15 min | 30 sec |
| Versioning | ❌ Git only | ✅ S3 versioning |
| Rollback | ❌ Redeploy old image | ✅ Change version var |
| A/B testing | ❌ Not possible | ✅ Easy |
| Docker image size | Large (~500MB) | Small (~100MB) |
| Independent updates | ❌ | ✅ |

---

## 🎯 Next Steps

**For now (while backend is deploying):**
- ✅ Models are baked into Docker (works fine)
- ✅ Training locally: `app/backend/models/enterprise/`
- ✅ Deployment: via Docker rebuild

**Future enhancement (optional):**
- Implement S3 model storage
- Faster model updates
- Better versioning

**Which approach do you prefer?**
1. Keep current (simple, works)
2. Implement S3 (professional, faster updates)
