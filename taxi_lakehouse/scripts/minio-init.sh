#!/bin/sh
# =============================================================================
# minio-init.sh — One-shot MinIO bootstrap
# Runs inside the minio/mc init container (see docker-compose.yml).
# Creates:
#   - Alias for the root account
# Creates:
#   - Alias for the root account
#   - Buckets: bronze, silver, gold
#   - Service account (pipeline credentials, NOT root)
#   - Bucket policy: read/write for pipeline account across all 3 buckets
# =============================================================================
set -e

MC_ALIAS="local"
ENDPOINT="http://minio:9000"

BRONZE_BUCKET="${MINIO_BUCKET_BRONZE:-bronze}"
SILVER_BUCKET="${MINIO_BUCKET_SILVER:-silver}"
GOLD_BUCKET="${MINIO_BUCKET_GOLD:-gold}"

echo ">>> Waiting for MinIO to be ready..."
until mc alias set "$MC_ALIAS" "$ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" 2>/dev/null; do
  sleep 2
done
echo ">>> MinIO ready."

# ── Clean buckets if requested (--clean or CLEAN_MINIO=true) ────────────────
if [ "$1" = "--clean" ] || [ "$CLEAN_MINIO" = "true" ]; then
  echo ">>> [CLEAN MODE] Removing all existing data from buckets..."
  for BUCKET in "$BRONZE_BUCKET" "$SILVER_BUCKET" "$GOLD_BUCKET"; do
    mc rm --recursive --force --dangerous "${MC_ALIAS}/${BUCKET}/" 2>/dev/null || true
  done
  echo ">>> All buckets cleared."
fi

# ── Create buckets ──────────────────────────────────────────────────────────
for BUCKET in "$BRONZE_BUCKET" "$SILVER_BUCKET" "$GOLD_BUCKET"; do
  echo ">>> Creating bucket: ${BUCKET}"
  mc mb --ignore-existing "${MC_ALIAS}/${BUCKET}"
  mc anonymous set none "${MC_ALIAS}/${BUCKET}"
done

# ── Create pipeline service account ───────────────────────────────────────
echo ">>> Creating pipeline service account..."
# Remove if already exists (idempotent)
mc admin user remove "$MC_ALIAS" "$MINIO_PIPELINE_ACCESS_KEY" 2>/dev/null || true

mc admin user add "$MC_ALIAS" "$MINIO_PIPELINE_ACCESS_KEY" "$MINIO_PIPELINE_SECRET_KEY"

# ── Create policy: read/write on bronze, silver, and gold buckets ─────────
cat > /tmp/pipeline-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:ListBucketMultipartUploads",
        "s3:ListMultipartUploadParts",
        "s3:AbortMultipartUpload"
      ],
      "Resource": [
        "arn:aws:s3:::${BRONZE_BUCKET}",
        "arn:aws:s3:::${BRONZE_BUCKET}/*",
        "arn:aws:s3:::${SILVER_BUCKET}",
        "arn:aws:s3:::${SILVER_BUCKET}/*",
        "arn:aws:s3:::${GOLD_BUCKET}",
        "arn:aws:s3:::${GOLD_BUCKET}/*"
      ]
    }
  ]
}
EOF

mc admin policy create "$MC_ALIAS" pipeline-rw /tmp/pipeline-policy.json
mc admin policy attach "$MC_ALIAS" pipeline-rw --user "$MINIO_PIPELINE_ACCESS_KEY"

echo ">>> MinIO init complete."
echo "    Buckets   : ${BRONZE_BUCKET}, ${SILVER_BUCKET}, ${GOLD_BUCKET}"
echo "    Access Key: ${MINIO_PIPELINE_ACCESS_KEY}"
