# ==========================================
# Stage 1: Builder (Aiven Source Connectors)
# ==========================================
FROM debian:bookworm-slim AS builder
RUN apt-get update && apt-get install -y openjdk-17-jdk git curl maven unzip && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY build_connectors.sh .
RUN chmod +x build_connectors.sh && ./build_connectors.sh

# ==========================================
# Stage 2: Downloader (All Pre-compiled Binaries)
# ==========================================
FROM debian:bookworm-slim AS downloader
RUN apt-get update && apt-get install -y curl tar unzip && rm -rf /var/lib/apt/lists/*
WORKDIR /downloads
COPY fetch_dependencies.sh .
RUN chmod +x fetch_dependencies.sh && ./fetch_dependencies.sh

# ==========================================
# Stage 3: Final Ephemeral Runtime
# ==========================================
FROM debian:bookworm-slim
WORKDIR /workspace

# 1. Copy Aiven JARs from Builder
COPY --from=builder /build/aiven-jdbc/build/libs/*-all.jar /workspace/connect/aiven-jdbc/
COPY --from=builder /build/aiven-s3/s3-sink-connector/build/libs/*-all.jar /workspace/connect/aiven-s3-sink/
COPY --from=builder /build/aiven-s3/s3-source-connector/build/libs/*-all.jar /workspace/connect/aiven-s3-source/

# 2. Copy ALL downloaded binaries from Downloader
COPY --from=downloader /downloads/connect /workspace/connect/
COPY --from=downloader /downloads/flink /workspace/flink/
COPY --from=downloader /downloads/spark /workspace/spark/
COPY --from=downloader /downloads/shared /workspace/shared/

# Final cleanup
RUN find /workspace -type f -name "*hadoop-core*" -delete

RUN echo "✅ DataML Stack Dependencies populated."

# Satisfies JSONArgsRecommended while allowing globbing/chaining
CMD ["/bin/sh", "-c", "cp -r /workspace/* /mnt/shared-deps/ && echo '✅ DataML Stack Dependencies populated.'"]
