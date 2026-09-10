"""
Validates the Airbyte S3 sync by:
1. Listing all Parquet files under the bookings/ prefix in S3
2. Downloading each into memory and counting total rows
3. Printing a small sample of records to eyeball the schema (booking_id, updated_at, etc.)

Credentials are loaded from a .env file in the same folder (never hardcoded here).
Before running, make sure your .env file contains:
    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    AWS_REGION=us-east-1

Then run:
    python validate_s3_sync.py
"""

import os
import io
import boto3
import pyarrow.parquet as pq
from dotenv import load_dotenv

load_dotenv()  # reads the .env file in the current folder

# ---------- CONFIG ----------
BUCKET_NAME = "voyage-data-plateform-yuvaraj-india"   # your actual bucket name
PREFIX = "raw/airbyte/bookings/"                       # the folder Airbyte wrote into
# -----------------------------

AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

print(f"Listing objects under s3://{BUCKET_NAME}/{PREFIX} ...")
paginator = s3.get_paginator("list_objects_v2")
parquet_keys = []
for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):
    for obj in page.get("Contents", []):
        if obj["Key"].endswith(".parquet"):
            parquet_keys.append(obj["Key"])

print(f"Found {len(parquet_keys)} Parquet file(s).\n")

total_rows = 0
sample_shown = False

for key in parquet_keys:
    resp = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    buffer = io.BytesIO(resp["Body"].read())
    table = pq.read_table(buffer)
    row_count = table.num_rows
    total_rows += row_count
    print(f"  {key}: {row_count} rows")

    if not sample_shown:
        print("\nSample of first 3 records from this file (schema check):")
        print(table.to_pandas().head(3).to_string())
        print()
        sample_shown = True

print(f"\nTOTAL ROWS ACROSS ALL FILES: {total_rows}")
print("Expected from Postgres: 119389 (run the psql command separately to confirm)")

## validation using docker container: docker exec -it voyage-postgres psql -U voyage_user -d voyage -c "SELECT COUNT(*) FROM bookings;"