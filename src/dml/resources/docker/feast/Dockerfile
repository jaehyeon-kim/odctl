FROM python:3.13-slim

WORKDIR /opt/feast/feature_repo

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/open-dataml-stack"
LABEL org.opencontainers.image.description="Custom Feast Feature Server engine optimized for the Open DataML Stack. Orchestrates low-latency feature serving via Valkey online caching, Postgres state storage, and ClickHouse analytical offline targets."

RUN pip install --no-cache-dir \
    'feast[clickhouse,redis,aws,postgres]' \
    clickhouse-connect \
    psycopg2-binary

# Add startup wrapper for dynamic pip installs
RUN printf '#!/bin/bash\n\
if [ -n "$_PIP_ADDITIONAL_REQUIREMENTS" ]; then\n\
  echo "📦 Installing extra packages: $_PIP_ADDITIONAL_REQUIREMENTS"\n\
  pip install --no-cache-dir $_PIP_ADDITIONAL_REQUIREMENTS\n\
fi\n\
exec "$@"\n' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
