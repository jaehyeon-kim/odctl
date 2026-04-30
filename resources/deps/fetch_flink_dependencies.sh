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

echo "▶️  Resolving Flink Versions..."
FLINK_V=$(get_maven_version "org/apache/flink/flink-core" "1\.[0-9]+\.[0-9]+")
if [ -z "$FLINK_V" ]; then echo "❌ Error: Could not resolve Flink core version!"; exit 1; fi

FLINK_MINOR=$(echo "$FLINK_V" | grep -Eo '^[0-9]+\.[0-9]+' || true)

ICEBERG_V=$(get_maven_version "org/apache/iceberg/iceberg-core" "[0-9]+\.[0-9]+\.[0-9]+")
if [ -z "$ICEBERG_V" ]; then echo "❌ Error: Could not resolve Iceberg core version!"; exit 1; fi

echo "▶️  Fetching Flink Dependencies for ${FLINK_MINOR}..."
make_dir "flink/1.x"

# Iceberg
fetch_artifact "flink/1.x/iceberg-runtime.jar" "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-flink-runtime-${FLINK_MINOR}/${ICEBERG_V}/iceberg-flink-runtime-${FLINK_MINOR}-${ICEBERG_V}.jar"

# Kafka
K_V=$(get_maven_version "org/apache/flink/flink-sql-connector-kafka" "[0-9]+\.[0-9]+\.[0-9]+-${FLINK_MINOR}")
if [ -z "$K_V" ]; then echo "❌ Error: Kafka connector for Flink ${FLINK_MINOR} is not published yet!"; exit 1; fi
fetch_artifact "flink/1.x/kafka.jar" "https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/${K_V}/flink-sql-connector-kafka-${K_V}.jar"

# JDBC
J_V=$(get_maven_version "org/apache/flink/flink-connector-jdbc" "[0-9]+\.[0-9]+\.[0-9]+-${FLINK_MINOR}")
if [ -z "$J_V" ]; then echo "❌ Error: JDBC connector for Flink ${FLINK_MINOR} is not published yet!"; exit 1; fi
fetch_artifact "flink/1.x/jdbc.jar" "https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/${J_V}/flink-connector-jdbc-${J_V}.jar"

# Fluss
F_V=$(get_maven_version "org/apache/fluss/fluss-flink-${FLINK_MINOR}" "[0-9]+\.[0-9]+\.[0-9]+(-incubating)?")
if [ -z "$F_V" ]; then echo "❌ Error: Fluss connector for Flink ${FLINK_MINOR} is not published yet!"; exit 1; fi
fetch_artifact "flink/1.x/fluss.jar" "https://repo1.maven.org/maven2/org/apache/fluss/fluss-flink-${FLINK_MINOR}/${F_V}/fluss-flink-${FLINK_MINOR}-${F_V}.jar"

echo "✅ Flink dependencies complete!"
