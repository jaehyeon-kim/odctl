FROM ghcr.io/mlflow/mlflow:v3.16.0-full

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/odctl"
LABEL org.opencontainers.image.description="MLflow tracking server and model server for the Open Data Stack, with the ONNX, XGBoost, LightGBM and PyTorch runtimes."

# libgomp1 is the OpenMP runtime. Without it both LightGBM and XGBoost install
# cleanly and then fail at import with:
#   OSError: libgomp.so.1: cannot open shared object file
# curl is for the compose healthchecks; the base image ships neither.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Install the model runtimes `mlflow models serve` loads a flavour with.
# Pinned to a minor, because a model is logged by one version and loaded back by
# whichever version this image last built with. An unpinned rebuild can move a
# runtime under a stored model and change its predictions or refuse to load it.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
    'onnxruntime~=1.29.0' \
    'xgboost~=3.2.0' \
    'lightgbm~=4.7.0'

# CPU torch from PyTorch's own index, since PyPI ships the CUDA build.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install 'torch~=2.14.0' --index-url https://download.pytorch.org/whl/cpu

# Open Data standard startup wrapper. The base image has no equivalent, unlike
# the official Airflow image, which implements this variable itself. It stays
# because a model's own library must be importable in this container before
# `mlflow models serve` can unpickle it, and installing one package is cheaper
# than rebuilding a multi-gigabyte image.
RUN printf '#!/bin/bash\n\
if [ -n "$_PIP_ADDITIONAL_REQUIREMENTS" ]; then\n\
  echo "📦 Installing extra packages: $_PIP_ADDITIONAL_REQUIREMENTS"\n\
  pip install --no-cache-dir $_PIP_ADDITIONAL_REQUIREMENTS\n\
fi\n\
exec "$@"\n' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
