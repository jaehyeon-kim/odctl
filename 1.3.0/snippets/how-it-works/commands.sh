# Commands from docs/how-it-works.md. .github/scripts/smoke.sh runs dry-run,
# reach, pull, up-pull, tag-override, workspace-flag and recreate-pull in the
# catalog case, seaweed-memory and create-bucket in the storage case,
# trino-port in the trino case, airflow-deps in the airflow case,
# mlops-deps and timezone in the mlflow case, and metadata-deps and
# metadata-autopilot in the metadata case.

# --8<-- [start:dry-run]
odctl up flink-lite --dry-run
# --8<-- [end:dry-run]

# --8<-- [start:reach]
docker run --rm --network odctl curlimages/curl:8.17.0 -s http://catalog:8181/v1/config
# --8<-- [end:reach]

# --8<-- [start:pull]
odctl pull catalog
# --8<-- [end:pull]

# --8<-- [start:up-pull]
odctl up catalog --pull
# --8<-- [end:up-pull]

# --8<-- [start:tag-override]
TAG=1.1.0 odctl explain postgres | grep odctl/postgres
# --8<-- [end:tag-override]

# --8<-- [start:workspace-flag]
odctl --workspace ./.odctl ps catalog
# --8<-- [end:workspace-flag]

# --8<-- [start:seaweed-memory]
sed -i.bak -e '/^  seaweed:/,/^  [a-z]/ s/mem_limit: 512m/mem_limit: 2g/' \
  -e '/^  seaweed:/,/^  [a-z]/ s/GOMEMLIMIT: 384MiB/GOMEMLIMIT: 1536MiB/' .odctl/compose-infra.yml
odctl recreate storage
docker inspect seaweed --format '{{.HostConfig.Memory}}'
# --8<-- [end:seaweed-memory]

# --8<-- [start:recreate-pull]
odctl recreate catalog --pull
# --8<-- [end:recreate-pull]

# --8<-- [start:trino-port]
sed -i.bak 's/"127.0.0.1:8080:8080" # Trino/"127.0.0.1:8180:8080" # Trino/' .odctl/compose-analytics.yml
odctl recreate trino
docker port trino
# --8<-- [end:trino-port]

# --8<-- [start:airflow-deps]
sed -i.bak 's/^_AIRFLOW_PIP_DEPS=.*/_AIRFLOW_PIP_DEPS="dateparser==1.4.3"/' .odctl/.env
odctl recreate airflow
docker exec airflow python -c "import dateparser; print(dateparser.__version__)"
# --8<-- [end:airflow-deps]

# --8<-- [start:metadata-deps]
sed -i.bak 's/^_METADATA_PIP_DEPS=.*/_METADATA_PIP_DEPS="dateparser==1.4.3"/' .odctl/.env
odctl recreate metadata
docker exec openmetadata-ingestion python -c "import dateparser; print(dateparser.__version__)"
# --8<-- [end:metadata-deps]

# --8<-- [start:metadata-autopilot]
sed -i.bak 's/^METADATA_AUTOPILOT=.*/METADATA_AUTOPILOT="true"/' .odctl/.env
odctl recreate metadata
docker logs openmetadata-init 2>&1 | tail -1
# --8<-- [end:metadata-autopilot]

# --8<-- [start:mlops-deps]
sed -i.bak 's/^_MLOPS_PIP_DEPS=.*/_MLOPS_PIP_DEPS="tabulate==0.9.0"/' .odctl/.env
odctl recreate mlflow
docker exec mlflow-serve python -c "import tabulate; print(tabulate.__version__)"
# --8<-- [end:mlops-deps]

# --8<-- [start:timezone]
sed -i.bak 's/^TZ=.*/TZ=Australia\/Sydney/' .odctl/.env
odctl recreate mlflow
docker exec mlflow date +%Z
# --8<-- [end:timezone]

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

# --8<-- [start:init-force]
odctl init --force --yes
# --8<-- [end:init-force]
