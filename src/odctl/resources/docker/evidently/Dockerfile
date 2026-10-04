FROM evidently/evidently-service:0.7.23

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/odctl"
LABEL org.opencontainers.image.description="Evidently UI service for the Open Data Stack, with s3fs so datasets can be stored on SeaweedFS."

# The base image installs evidently[sql] only, so an s3:// dataset_storage path
# fails with no filesystem for the s3 protocol. s3fs pins fsspec to its own
# version, and the base image ships fsspec 2026.7.0, so s3fs stays on the same
# version. Move both together when the base image moves fsspec, or pip
# replaces the fsspec that evidently was installed with.
RUN pip install --no-cache-dir 's3fs==2026.7.0'

# ENTRYPOINT is inherited: `evidently ui --host 0.0.0.0`.
