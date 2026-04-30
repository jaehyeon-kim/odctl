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

# Copy all individual fetch scripts
COPY fetch_flink_dependencies.sh .
COPY fetch_spark_dependencies.sh .
COPY fetch_shared_dependencies.sh .
COPY fetch_schema_dependencies.sh .

# Make them executable and run them
RUN chmod +x *.sh \
    && ./fetch_shared_dependencies.sh \
    && ./fetch_flink_dependencies.sh \
    && ./fetch_spark_dependencies.sh \
    && ./fetch_schema_dependencies.sh

# ==========================================
# Stage 3: Final Ephemeral Runtime
# ==========================================
FROM debian:bookworm-slim

WORKDIR /workspace

# Copy Aiven JARs from Builder
COPY --from=builder /build/dist/ /workspace/connect/

# Copy ALL downloaded binaries from Downloader
COPY --from=downloader /downloads/connect /workspace/connect/
COPY --from=downloader /downloads/flink /workspace/flink/
COPY --from=downloader /downloads/spark /workspace/spark/
COPY --from=downloader /downloads/shared /workspace/shared/

# Move Confluent Converters into the Connect plugin directory
RUN mv /workspace/shared/confluent-converters /workspace/connect/confluent-converters

# Final cleanup
RUN find /workspace -type f -name "*hadoop-core*" -delete

RUN echo "✅ DataML Stack Dependencies populated."

# Satisfies JSONArgsRecommended while allowing globbing/chaining
CMD ["/bin/sh", "-c", "cp -r /workspace/* /mnt/shared-deps/ && echo '✅ DataML Stack Dependencies populated.'"]
