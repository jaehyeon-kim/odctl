FROM ghcr.io/mlflow/mlflow:v3.12.0-full

# Install the Postgres and S3 storage connectors
RUN pip install --no-cache-dir \
    psycopg2-binary \
    boto3

# Add startup wrapper for dynamic pip installs
RUN printf '#!/bin/bash\n\
if [ -n "$_PIP_ADDITIONAL_REQUIREMENTS" ]; then\n\
  echo "📦 Installing extra packages: $_PIP_ADDITIONAL_REQUIREMENTS"\n\
  pip install --no-cache-dir $_PIP_ADDITIONAL_REQUIREMENTS\n\
fi\n\
exec "$@"\n' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
