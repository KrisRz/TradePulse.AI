# TradePulse.AI - Enhanced Terraform Infrastructure

Minimalna, tania infrastruktura serverless AWS dla TradePulse.AI z ulepszeniami:
- **S3 + CloudFront** (frontend z cache policies)
- **HTTP API Gateway + Lambda** (backend za CloudFront)
- **DynamoDB** (database)
- **Route53 + ACM** (custom domain + SSL)
- **SSM Parameter Store** (sekrety)
- **S3 + DynamoDB** (terraform state)

Region: `eu-west-2` (London)

## 📁 Struktura

```
infra/terraform/
├── global/bootstrap/          # Jednorazowo: bucket tfstate + locks
├── modules/
│   ├── dynamodb/             # DynamoDB table
│   ├── api_lambda/           # HTTP API + Lambda
│   ├── frontend_static_site/ # S3 + CloudFront z API origin
│   ├── dns_acm/             # Route53 + ACM certyfikaty
│   └── ssm_params/          # SSM Parameter Store
└── envs/
    ├── dev/                  # Development environment
    └── prod/                 # Production environment
```

## 🚀 Kolejność deploymentu

### 1. Bootstrap (jednorazowo)
```bash
cd infra/terraform/global/bootstrap
terraform init
terraform apply -var "tfstate_bucket_name=kris-tfstate-eu-west-2"
```

### 2. Development Environment
```bash
cd infra/terraform/envs/dev
cp terraform.tfvars.example terraform.tfvars
# Edytuj terraform.tfvars
terraform init
terraform plan
terraform apply
```

### 3. Production Environment
```bash
cd infra/terraform/envs/prod
cp terraform.tfvars.example terraform.tfvars
# Edytuj terraform.tfvars
terraform init
terraform plan
terraform apply
```

## ⚙️ Konfiguracja

### Zmienne w terraform.tfvars:
- `app_name` - nazwa aplikacji (np. "tradepulse")
- `lambda_zip_path` - ścieżka do ZIP-a z backendem
- `create_cloudfront` - czy tworzyć CloudFront (true/false)
- `root_domain` - główna domena (np. "tradepulse.ai")
- `app_subdomain` - subdomena aplikacji (np. "app")

## 🌐 Custom Domain Setup

1. **Kup domenę** (np. tradepulse.ai)
2. **Przekieruj NS** na serwery Route53 (z output `name_servers`)
3. **Wdróż infrastrukturę** - automatycznie utworzy:
   - Hosted Zone w Route53
   - Certyfikat ACM w us-east-1
   - Rekordy DNS dla walidacji
   - CloudFront z custom domain

## 🔧 Backend Lambda

Przygotuj ZIP z backendem:
```bash
cd app/backend
npm run build
zip -r dist/backend.zip dist/
```

## 🌐 Frontend

Wgraj pliki do S3 bucket:
```bash
aws s3 sync app/frontend/dist/ s3://tradepulse-dev-site/
```

## 🔒 Sekrety (SSM Parameter Store)

Dodaj sekrety przez AWS Console lub odkomentuj moduł w main.tf:
```hcl
module "secrets" {
  source      = "../../modules/ssm_params"
  path_prefix = "/tradepulse/dev"
  secrets = {
    BINANCE_API_KEY   = "***"
    BINANCE_SECRET_KEY= "***"
    JWT_SECRET_KEY    = "***"
  }
}
```

## 💰 Koszty

- **Minimalne** - płacisz tylko za użycie
- **Bez VPC/NAT** - oszczędność
- **PAY_PER_REQUEST** - DynamoDB
- **Serverless** - Lambda + API Gateway
- **CloudFront** - płacisz za transfer

## 🔒 Bezpieczeństwo

- Wszystkie buckety S3 są prywatne
- CloudFront używa Origin Access Control (OAC)
- DynamoDB z szyfrowaniem
- Lambda z minimalnymi uprawnieniami
- Custom domain z SSL
- Sekrety w SSM Parameter Store

## 🚀 Ulepszenia vs poprzednia wersja

1. **Custom Domain** - Route53 + ACM
2. **API za CloudFront** - lepsze cache i bezpieczeństwo
3. **Cache Policies** - zaawansowane polityki cache
4. **SSM Parameters** - zarządzanie sekretami
5. **Provider Aliases** - obsługa us-east-1 dla ACM
6. **Enhanced IAM** - uprawnienia do SSM
