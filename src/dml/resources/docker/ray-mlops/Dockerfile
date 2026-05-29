FROM rayproject/ray:2.55.1-py312-cpu

LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/open-dataml-stack"
LABEL org.opencontainers.image.description="Unified Ray Serve and MLflow image for the Open DataML Stack. Handles inference deployment, experiment tracking, and direct ClickHouse/Kafka connections."

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

USER ray

# Inline pip installation to preserve a single file deployment structure
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    # MLOps & Serving Core
    'mlflow~=3.12.0' \
    fastapi \
    uvicorn \
    # Database Driver (Required for Postgres tracking backend)
    psycopg2-binary \
    # Inference Engines (Required for Deserialization)
    torch \
    stable-baselines3 \
    gymnasium \
    scikit-learn \
    xgboost \
    lightgbm \
    pandas \
    numpy \
    # Storage, Lakehouse & Message Routing Drivers
    clickhouse-connect \
    "pyiceberg[s3fs,pyarrow]" \
    boto3 \
    kafka-python \
    aiokafka \
    valkey

# Add the Open DataML standard startup wrapper for dynamic pip installs at runtime
USER root

RUN printf '#!/bin/bash\n\
if [ -n "$_PIP_ADDITIONAL_REQUIREMENTS" ]; then\n\
  echo "📦 Installing extra packages: $_PIP_ADDITIONAL_REQUIREMENTS"\n\
  pip install --no-cache-dir $_PIP_ADDITIONAL_REQUIREMENTS\n\
fi\n\
exec "$@"\n' > /entrypoint.sh && chmod +x /entrypoint.sh

# Revert to the unprivileged ray user
USER ray

EXPOSE 8000 8265 5000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
