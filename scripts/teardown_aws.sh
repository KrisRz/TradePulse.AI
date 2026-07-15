#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="/Applications/Projects/TradePulse.AI"
INFRA_DIR="${ROOT_DIR}/infra"

STATE_BUCKET="tradepulse-terraform-state-590183672693"
LOCK_TABLE="tradepulse-terraform-locks"
BACKEND_REGION="eu-west-2"

echo ">>> TradePulse.AI AWS teardown starting..."
echo "Root dir:      ${ROOT_DIR}"
echo "Infra dir:     ${INFRA_DIR}"
echo "State bucket:  ${STATE_BUCKET} (region: ${BACKEND_REGION})"
echo "Lock table:    ${LOCK_TABLE}"
echo

if ! command -v terraform >/dev/null 2>&1; then
  echo "ERROR: terraform not found in PATH. Install Terraform >= 1.5 and retry." >&2
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "ERROR: aws CLI not found in PATH. Install awscli and retry." >&2
  exit 1
fi

if [ ! -d "${INFRA_DIR}" ]; then
  echo "ERROR: Infra directory not found at ${INFRA_DIR}" >&2
  exit 1
fi

cd "${INFRA_DIR}"

echo ">>> Running terraform init (using remote S3 backend)..."
terraform init -upgrade -input=false

echo ">>> Destroying all Terraform workspaces..."
workspaces_raw="$(terraform workspace list)"
workspaces="$(printf '%s\n' "${workspaces_raw}" | sed 's/*//g' | tr -d ' ' | sed '/^$/d')"

for ws in ${workspaces}; do
  echo
  echo "=== Workspace: ${ws} ==="
  terraform workspace select "${ws}" >/dev/null
  echo "Running terraform destroy in workspace '${ws}'..."
  terraform destroy -auto-approve
done

echo
echo ">>> Terraform destroys completed for all workspaces."

echo
echo ">>> Cleaning up Terraform backend state bucket and lock table (hard delete)..."

echo "Deleting all objects from s3://${STATE_BUCKET} (if it exists)..."
aws s3 rm "s3://${STATE_BUCKET}" --recursive --region "${BACKEND_REGION}" || true

echo "Deleting state bucket s3://${STATE_BUCKET}..."
aws s3 rb "s3://${STATE_BUCKET}" --force --region "${BACKEND_REGION}" || true

echo "Deleting DynamoDB lock table ${LOCK_TABLE} in region ${BACKEND_REGION}..."
aws dynamodb delete-table \
  --table-name "${LOCK_TABLE}" \
  --region "${BACKEND_REGION}" >/dev/null 2>&1 || true

echo
echo ">>> TradePulse.AI AWS teardown completed."


