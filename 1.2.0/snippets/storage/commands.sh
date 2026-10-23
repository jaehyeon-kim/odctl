# Commands from docs/how-it-works.md. .github/scripts/smoke.sh runs each section
# in the storage case.

# --8<-- [start:create-bucket]
docker run --rm -i --network odctl python:3.12-slim \
  sh -c 'pip install -q --root-user-action=ignore boto3==1.43.118 && python -' <<'PY'
import boto3
s3 = boto3.client("s3", endpoint_url="http://seaweed:8333", region_name="us-east-1",
                  aws_access_key_id="user", aws_secret_access_key="password")
s3.create_bucket(Bucket="desflow")
print(sorted(b["Name"] for b in s3.list_buckets()["Buckets"]))
PY
# --8<-- [end:create-bucket]
