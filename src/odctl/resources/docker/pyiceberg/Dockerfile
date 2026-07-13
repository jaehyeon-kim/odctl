FROM python:3.12-slim

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/odctl"
LABEL org.opencontainers.image.description="Minimal PyIceberg CLI headless sidecar container used to safely execute native Iceberg metadata operations and catalog tables via host 'odctl iceberg' commands."

# Pre-bake the dependencies into the image layer
RUN pip install --no-cache-dir 'pyiceberg[s3fs,pyarrow]'

CMD ["bash"]
