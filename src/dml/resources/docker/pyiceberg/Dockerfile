FROM python:3.12-slim

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/open-dataml-stack"
LABEL org.opencontainers.image.description="Minimal PyIceberg CLI headless sidecar container used to safely execute native Iceberg metadata operations and catalog tables via host 'dml iceberg' commands."

# Pre-bake the dependencies into the image layer
RUN pip install --no-cache-dir 'pyiceberg[s3fs]'

CMD ["bash"]
