# ==========================================
# Stage 1: Source Builder (Aiven Connectors)
# ==========================================
FROM debian:bookworm-slim AS source-builder
RUN apt-get update && apt-get install -y openjdk-17-jdk git curl maven unzip && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY build_connectors.sh .
RUN chmod +x build_connectors.sh && ./build_connectors.sh

# ==========================================
# Stage 2: Gradle Resolver (Schema Converters)
# ==========================================
FROM gradle:8.6-jdk17 AS gradle-resolver
WORKDIR /app
COPY build.gradle .
# Let Gradle do the heavy transitive lifting!
RUN gradle copyDependencies --no-daemon

# ==========================================
# Stage 3: Direct Downloader (Uber JARs & ZIPs)
# ==========================================
FROM debian:bookworm-slim AS downloader
RUN apt-get update && apt-get install -y curl tar unzip && rm -rf /var/lib/apt/lists/*
WORKDIR /downloads
# Copy the standalone fetch scripts
COPY fetch_standalone_plugins.sh .
COPY fetch_flink_dependencies.sh .
COPY fetch_spark_dependencies.sh .
# Execute the direct downloads
RUN chmod +x *.sh \
    && ./fetch_standalone_plugins.sh \
    && ./fetch_flink_dependencies.sh \
    && ./fetch_spark_dependencies.sh

# ==========================================
# Stage 4: Final Ephemeral Runtime
# ==========================================
FROM debian:bookworm-slim
WORKDIR /workspace

# 1. Grab source-built Aiven JARs
COPY --from=source-builder /build/dist/ /workspace/connect/

# 2. Grab perfectly resolved Schema Converters
COPY --from=gradle-resolver /app/build/confluent-converters/ /workspace/connect/confluent-converters/

# 3. Grab standalone Uber JARs & ZIPs
COPY --from=downloader /downloads/connect /workspace/connect/
COPY --from=downloader /downloads/flink /workspace/flink/
COPY --from=downloader /downloads/spark /workspace/spark/

# Final cleanup
RUN find /workspace -type f -name "*hadoop-core*" -delete

RUN echo "✅ DataML Stack Dependencies populated."

# Satisfies JSONArgsRecommended while allowing globbing/chaining
CMD ["/bin/sh", "-c", "cp -r /workspace/* /mnt/shared-deps/ && echo '✅ DataML Stack Dependencies populated.'"]
