#!/bin/bash
# Create the S3 bucket that holds the Terraform state for infra-serverless/.
#
# Chicken-and-egg: the state backend cannot be managed by the state it stores,
# so this one bucket is bootstrapped outside Terraform. Everything else in the
# stack stays in Terraform.
#
# Idempotent — safe to re-run; it only creates what is missing.
#
# Why S3 at all: the state was a single file on one laptop. Losing it means
# rebuilding the whole stack (Lambdas, DynamoDB, scheduler, alarms, DNS, ACM)
# by hand against live resources. Versioning also means a corrupt write is
# recoverable instead of terminal.
#
# Locking uses S3 conditional writes (`use_lockfile = true`, Terraform >= 1.10),
# so no DynamoDB lock table is needed — one less resource and one less bill.
set -euo pipefail

REGION="${AWS_REGION:-eu-west-2}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${TF_STATE_BUCKET:-tradepulse-tfstate-${ACCOUNT}}"

echo "account : ${ACCOUNT}"
echo "region  : ${REGION}"
echo "bucket  : ${BUCKET}"

if aws s3api head-bucket --bucket "${BUCKET}" 2>/dev/null; then
    echo "bucket already exists — verifying settings"
else
    echo "creating bucket"
    aws s3api create-bucket \
        --bucket "${BUCKET}" \
        --region "${REGION}" \
        --create-bucket-configuration "LocationConstraint=${REGION}" >/dev/null
    aws s3api wait bucket-exists --bucket "${BUCKET}"
fi

# Versioning: every state write keeps the previous version, so a bad apply or a
# truncated upload can be rolled back. This is the single most important
# setting on a state bucket.
aws s3api put-bucket-versioning \
    --bucket "${BUCKET}" \
    --versioning-configuration Status=Enabled

# SSE-S3 (free). The state contains resource IDs and ARNs, not secrets, but
# encryption at rest costs nothing here.
aws s3api put-bucket-encryption \
    --bucket "${BUCKET}" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
            "BucketKeyEnabled": true
        }]
    }'

# State must never be publicly reachable.
aws s3api put-public-access-block \
    --bucket "${BUCKET}" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Reject any plaintext (non-TLS) request.
aws s3api put-bucket-policy --bucket "${BUCKET}" --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
        \"Sid\": \"DenyInsecureTransport\",
        \"Effect\": \"Deny\",
        \"Principal\": \"*\",
        \"Action\": \"s3:*\",
        \"Resource\": [
            \"arn:aws:s3:::${BUCKET}\",
            \"arn:aws:s3:::${BUCKET}/*\"
        ],
        \"Condition\": {\"Bool\": {\"aws:SecureTransport\": \"false\"}}
    }]
}"

# No lifecycle rule on purpose: the state file is tens of kilobytes, so keeping
# every version costs fractions of a cent, and an expiration rule would quietly
# delete the recovery points this bucket exists to provide.

echo
echo "ready. Backend block (already in infra-serverless/main.tf):"
echo "  bucket       = \"${BUCKET}\""
echo "  key          = \"infra-serverless/terraform.tfstate\""
echo "  region       = \"${REGION}\""
echo
echo "migrate an existing local state with:"
echo "  terraform -chdir=infra-serverless init -migrate-state"
