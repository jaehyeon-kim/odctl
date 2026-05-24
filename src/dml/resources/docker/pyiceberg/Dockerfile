FROM python:3.12-slim

# Pre-bake the dependencies into the image layer
RUN pip install --no-cache-dir 'pyiceberg[s3fs]'

CMD ["bash"]
