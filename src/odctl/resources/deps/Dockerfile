# ==========================================
# Stage 1: Source Builder (Aiven Connectors)
# ==========================================
FROM debian:bookworm-slim AS source-builder
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y openjdk-17-jdk git curl maven unzip && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY build_connectors.sh .
RUN --mount=type=cache,target=/root/.gradle \
    chmod +x build_connectors.sh && ./build_connectors.sh

# ==========================================
# Stage 2: Gradle Resolver (Schema Converters & Flink Parquet)
# ==========================================
FROM gradle:8.6-jdk17 AS gradle-resolver
WORKDIR /app
COPY build.gradle .
# Let Gradle do the heavy transitive lifting for both Connect and Flink!
RUN --mount=type=cache,target=/home/gradle/.gradle \
    gradle copyAllDependencies --no-daemon

# ==========================================
# Stage 3: Direct Downloader (Uber JARs & ZIPs)
# ==========================================
FROM debian:bookworm-slim AS downloader
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y curl tar unzip && rm -rf /var/lib/apt/lists/*
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

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/odctl"
LABEL org.opencontainers.image.description="Ephemeral dependency initializer for the Open Data Stack. Automatically runs to populate the shared Docker volume with standalone plugins, Spark runtimes, Kafka converters, and Flink/Hadoop JARs before exiting."

# Grab source-built Aiven JARs
COPY --from=source-builder /build/dist/ /workspace/connect/

# Grab perfectly resolved Schema Converters
COPY --from=gradle-resolver /app/build/confluent-converters/ /workspace/connect/confluent-converters/

# Grab Gradle-resolved Flink Parquet & Hadoop JARs
COPY --from=gradle-resolver /app/build/flink-jars/ /workspace/flink/1.x/

# Grab standalone Uber JARs & ZIPs (Docker safely merges flink/1.x/ folders)
COPY --from=downloader /downloads/connect /workspace/connect/
COPY --from=downloader /downloads/flink /workspace/flink/
COPY --from=downloader /downloads/spark /workspace/spark/
COPY --from=downloader /downloads/shared /workspace/shared/

# Final cleanup (hadoop-client replaces legacy hadoop-core, so this delete is perfectly safe)
RUN find /workspace -type f -name "*hadoop-core*" -delete

RUN echo "✅ Open Data Stack Dependencies populated."

# Satisfies JSONArgsRecommended while allowing globbing/chaining
CMD ["/bin/sh", "-c", "cp -r /workspace/* /mnt/shared-deps/ && echo '✅ Open Data Stack Dependencies populated.'"]
