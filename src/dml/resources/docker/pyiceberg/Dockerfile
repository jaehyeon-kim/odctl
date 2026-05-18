FROM python:3.12-slim

# Pre-bake the dependencies into the image layer
RUN pip install --no-cache-dir 'pyiceberg[s3fs]'

# Keep the sidecar asleep until a dml command executes against it
CMD ["tail", "-f", "/dev/null"]
