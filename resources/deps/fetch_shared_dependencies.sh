#!/bin/bash
set -eo pipefail

DRY_RUN=0
if [[ "$1" == "dry-run" || "$1" == "--dry-run" ]]; then DRY_RUN=1; echo "⚠️  Running in DRY-RUN mode."; fi

make_dir() { if [ "$DRY_RUN" -eq 0 ]; then mkdir -p "$1"; fi; }
fetch_artifact() {
    if [ "$DRY_RUN" -eq 1 ]; then echo " 🔍 Checking: $2"; curl -sL -I -f "$2" > /dev/null || exit 1;
    else echo " ⬇️  Downloading: $2"; curl -sL -f -o "$1" "$2"; fi
}
get_maven_version() {
    curl -sL "https://repo1.maven.org/maven2/${1}/maven-metadata.xml" | grep -Eo "<version>${2}</version>" | sort -V | tail -1 | sed 's/<\/\?version>//g' || true
}

echo "▶️  Resolving Shared & Connector Versions..."
ICEBERG_V=$(get_maven_version "org/apache/iceberg/iceberg-core" "[0-9]+\.[0-9]+\.[0-9]+")
if [ -z "$ICEBERG_V" ]; then echo "❌ Error: Could not resolve Iceberg core version!"; exit 1; fi

POSTGRES_V=$(get_maven_version "org/postgresql/postgresql" "42\.[0-9]+\.[0-9]+")
if [ -z "$POSTGRES_V" ]; then echo "❌ Error: Could not resolve PostgreSQL driver version!"; exit 1; fi

DEB_V=$(get_maven_version "io/debezium/debezium-connector-postgres" "[0-9]+\.[0-9]+\.[0-9]+\.Final")
if [ -z "$DEB_V" ]; then echo "❌ Error: Could not resolve Debezium version!"; exit 1; fi

# Fetch GitHub metadata
ICEBERG_KC_JSON=$(curl -sL https://api.github.com/repos/databricks/iceberg-kafka-connect/releases/latest)
ICEBERG_KC_URL=$(echo "$ICEBERG_KC_JSON" | grep -Eo '"browser_download_url":\s*"[^"]+\.zip"' | grep -v 'hive' | head -1 | awk -F'"' '{print $4}' || true)
if [ -z "$ICEBERG_KC_URL" ]; then echo "❌ Error: Could not resolve Databricks Iceberg Kafka Connect URL! (Check GitHub rate limits)"; exit 1; fi

echo "▶️  Fetching Kafka Connectors..."
make_dir "connect/clickhouse-sink"
make_dir "connect/msk-datagen"
make_dir "connect/debezium-postgres"
make_dir "connect/redis"
make_dir "connect/iceberg-sink"

CH_URL=$(curl -sL https://api.github.com/repos/ClickHouse/clickhouse-kafka-connect/releases/latest | grep -Eo '"browser_download_url":\s*"[^"]+\.zip"' | head -1 | awk -F'"' '{print $4}' || true)
if [ -z "$CH_URL" ]; then echo "❌ Error: Could not resolve ClickHouse Kafka Connect URL!"; exit 1; fi
fetch_artifact "ch.zip" "$CH_URL"
if [ "$DRY_RUN" -eq 0 ]; then unzip -qq ch.zip -d connect/clickhouse-sink && rm ch.zip; fi

MSK_URL=$(curl -sL https://api.github.com/repos/awslabs/amazon-msk-data-generator/releases/latest | grep -Eo '"browser_download_url":\s*"[^"]+-dependencies\.jar"' | head -1 | awk -F'"' '{print $4}' || true)
if [ -z "$MSK_URL" ]; then echo "❌ Error: Could not resolve MSK Data Generator URL!"; exit 1; fi
fetch_artifact "connect/msk-datagen/msk-generator.jar" "$MSK_URL"

REDIS_URL=$(curl -sL https://api.github.com/repos/redis-field-engineering/redis-kafka-connect/releases/latest | grep -Eo '"browser_download_url":\s*"[^"]+\.zip"' | head -1 | awk -F'"' '{print $4}' || true)
if [ -z "$REDIS_URL" ]; then echo "❌ Error: Could not resolve Redis Kafka Connect URL!"; exit 1; fi
fetch_artifact "redis.zip" "$REDIS_URL"
if [ "$DRY_RUN" -eq 0 ]; then unzip -qq redis.zip -d connect/redis && rm redis.zip; fi

fetch_artifact "iceberg-sink.zip" "$ICEBERG_KC_URL"
if [ "$DRY_RUN" -eq 0 ]; then unzip -qq iceberg-sink.zip -d connect/iceberg-sink && rm iceberg-sink.zip; fi

fetch_artifact "deb.tar.gz" "https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/${DEB_V}/debezium-connector-postgres-${DEB_V}-plugin.tar.gz"
if [ "$DRY_RUN" -eq 0 ]; then tar -xzf deb.tar.gz -C connect/debezium-postgres --strip-components=1 && rm deb.tar.gz; fi

fetch_artifact "ol.tar.gz" "https://repo1.maven.org/maven2/io/debezium/debezium-openlineage-core/${DEB_V}/debezium-openlineage-core-${DEB_V}-libs.tar.gz"
if [ "$DRY_RUN" -eq 0 ]; then tar -xzf ol.tar.gz -C connect/debezium-postgres && rm ol.tar.gz; fi

echo "▶️  Fetching Shared Iceberg Dependencies..."
make_dir "shared"
fetch_artifact "shared/iceberg-aws-bundle.jar" "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_V}/iceberg-aws-bundle-${ICEBERG_V}.jar"
fetch_artifact "shared/postgresql.jar" "https://repo1.maven.org/maven2/org/postgresql/postgresql/${POSTGRES_V}/postgresql-${POSTGRES_V}.jar"

echo "✅ Shared & Connect dependencies complete!"
