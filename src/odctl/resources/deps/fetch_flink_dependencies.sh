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
    curl -sL "https://repo1.maven.org/maven2/${1}/maven-metadata.xml" | grep -Eo "<version>${2}</version>" | sort -V | tail -1 | sed -E 's#</?version>##g' || true
}

echo "▶️  Resolving Flink Versions..."

# 🔒 PINNED: Flink 2.1, not the latest 2.x. Iceberg publishes
# iceberg-flink-runtime for 2.0 and 2.1 only, and Fluss has no 2.0 build, so 2.1
# is the one minor where every connector this stack needs exists. See issue #9.
FLINK_MINOR="2.1"
FLINK_V=$(get_maven_version "org/apache/flink/flink-core" "${FLINK_MINOR}\.[0-9]+")
if [ -z "$FLINK_V" ]; then echo "❌ Error: Could not resolve Flink ${FLINK_MINOR} patch version!"; exit 1; fi

# 🔒 HARDCODED: Lock Iceberg to 1.11.0 to match Spark and PyIceberg sidecar
ICEBERG_V="1.11.0"

echo "▶️  Fetching Flink Dependencies for ${FLINK_MINOR} (Iceberg ${ICEBERG_V})..."
make_dir "flink/2.x"

# Iceberg Flink Runtime
fetch_artifact "flink/2.x/iceberg-runtime.jar" "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-flink-runtime-${FLINK_MINOR}/${ICEBERG_V}/iceberg-flink-runtime-${FLINK_MINOR}-${ICEBERG_V}.jar"

# Kafka (Flink's independent connector cycle)
K_V=$(get_maven_version "org/apache/flink/flink-sql-connector-kafka" "[0-9]+\.[0-9]+\.[0-9]+-${FLINK_MINOR}")
if [ -z "$K_V" ]; then echo "❌ Error: Kafka connector for Flink ${FLINK_MINOR} is not published yet!"; exit 1; fi
fetch_artifact "flink/2.x/kafka.jar" "https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/${K_V}/flink-sql-connector-kafka-${K_V}.jar"

# Avro with Confluent Schema Registry. This uber JAR is a superset of
# flink-sql-avro: it registers the plain 'avro' format factory as well as
# 'avro-confluent' and 'debezium-avro-confluent', so adding both would duplicate
# the Avro classes and register the same factory twice.
fetch_artifact "flink/2.x/avro-confluent-registry.jar" "https://repo1.maven.org/maven2/org/apache/flink/flink-sql-avro-confluent-registry/${FLINK_V}/flink-sql-avro-confluent-registry-${FLINK_V}.jar"

# JDBC. Flink 2.x split this connector: the core jar carries the connector and
# each dialect ships separately, so Postgres needs both. The Postgres driver
# itself comes from fetch_standalone_plugins.sh into shared/.
J_V=$(get_maven_version "org/apache/flink/flink-connector-jdbc-core" "[0-9]+\.[0-9]+\.[0-9]+-${FLINK_MINOR}")
if [ -z "$J_V" ]; then echo "❌ Error: JDBC connector for Flink ${FLINK_MINOR} is not published yet!"; exit 1; fi
fetch_artifact "flink/2.x/jdbc-core.jar" "https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc-core/${J_V}/flink-connector-jdbc-core-${J_V}.jar"
fetch_artifact "flink/2.x/jdbc-postgres.jar" "https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc-postgres/${J_V}/flink-connector-jdbc-postgres-${J_V}.jar"

# Fluss
F_V=$(get_maven_version "org/apache/fluss/fluss-flink-${FLINK_MINOR}" "[0-9]+\.[0-9]+\.[0-9]+(-incubating)?")
if [ -z "$F_V" ]; then echo "❌ Error: Fluss connector for Flink ${FLINK_MINOR} is not published yet!"; exit 1; fi
fetch_artifact "flink/2.x/fluss.jar" "https://repo1.maven.org/maven2/org/apache/fluss/fluss-flink-${FLINK_MINOR}/${F_V}/fluss-flink-${FLINK_MINOR}-${F_V}.jar"

echo "✅ Flink dependencies complete!"
