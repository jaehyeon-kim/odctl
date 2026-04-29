#!/bin/bash
set -e

DRY_RUN=0
if [[ "$1" == "dry-run" || "$1" == "--dry-run" ]]; then
    DRY_RUN=1
    echo "⚠️  Running in DRY-RUN mode. Validating artifact availability."
fi

make_dir() {
    if [ "$DRY_RUN" -eq 0 ]; then mkdir -p "$1"; fi
}

fetch_artifact() {
    local output_path=$1
    local url=$2
    if [ "$DRY_RUN" -eq 1 ]; then
        echo " 🔍 Checking: $url"
        if [[ -z "$url" ]]; then echo "    ❌ Error: URL is empty"; exit 1; fi
        if curl -sL -I -f "$url" > /dev/null; then echo "    ✅ Found"; else echo "    ❌ Missing: $url"; exit 1; fi
    else
        echo " ⬇️ Downloading: $url"
        curl -sL -f -o "$output_path" "$url"
    fi
}

get_maven_version() {
    local path=$1
    local regex=$2
    curl -sL "https://repo1.maven.org/maven2/${path}/maven-metadata.xml" | \
        grep -Eo "<version>${regex}</version>" | sort -V | tail -1 | sed 's/<\/\?version>//g' || true
}

## Version Resolution
ICEBERG_V=$(get_maven_version "org/apache/iceberg/iceberg-core" "[0-9]+\.[0-9]+\.[0-9]+")
FLINK_V=$(get_maven_version "org/apache/flink/flink-core" "1\.[0-9]+\.[0-9]+")
FLINK_MINOR=$(echo "$FLINK_V" | grep -Eo '^[0-9]+\.[0-9]+' || true)

SCALA_V="2.13"
SPARK_COMPAT_MINOR=$(curl -sL "https://repo1.maven.org/maven2/org/apache/iceberg/" | \
    grep -Eo "iceberg-spark-runtime-[0-9]+\.[0-9]+_${SCALA_V}" | \
    sed "s/iceberg-spark-runtime-//;s/_${SCALA_V}//" | sort -V | tail -1)
SPARK_V=$(get_maven_version "org/apache/spark/spark-core_${SCALA_V}" "${SPARK_COMPAT_MINOR}\.[0-9]+")

POSTGRES_V=$(get_maven_version "org/postgresql/postgresql" "42\.[0-9]+\.[0-9]+")
DEB_V=$(get_maven_version "io/debezium/debezium-connector-postgres" "[0-9]+\.[0-9]+\.[0-9]+\.Final")
OL_SPARK_V=$(get_maven_version "io/openlineage/openlineage-spark_${SCALA_V}" "[0-9]+\.[0-9]+\.[0-9]+")

OM_JSON=$(curl -s https://api.github.com/repos/open-metadata/openmetadata-spark-agent/releases/latest)
OM_V=$(echo "$OM_JSON" | grep -Eo '"tag_name":\s*"[^"]+"' | head -1 | awk -F'"' '{print $4}' | sed 's/^v//')
OM_SPARK_URL=$(echo "$OM_JSON" | grep -Eo '"browser_download_url":\s*"[^"]+\.jar"' | head -1 | awk -F'"' '{print $4}' || true)

# Iceberg Kafka Connect (Databricks/Tabular)
ICEBERG_KC_JSON=$(curl -s https://api.github.com/repos/databricks/iceberg-kafka-connect/releases/latest)
ICEBERG_KC_V=$(echo "$ICEBERG_KC_JSON" | grep -Eo '"tag_name":\s*"[^"]+"' | head -1 | awk -F'"' '{print $4}' | sed 's/^v//')
# grep -v 'hive' ensures we drop the hive distribution
ICEBERG_KC_URL=$(echo "$ICEBERG_KC_JSON" | grep -Eo '"browser_download_url":\s*"[^"]+\.zip"' | grep -v 'hive' | head -1 | awk -F'"' '{print $4}' || true)

echo "-------------------------------------------------------"
echo "✅ Resolved Versions for Open DataML Stack:"
echo " - Flink:        $FLINK_V"
echo " - Spark:        $SPARK_V (Scala $SCALA_V)"
echo " - Iceberg:      $ICEBERG_V"
echo " - Iceberg Sink: $ICEBERG_KC_V (No Hive)"
echo " - Debezium:     $DEB_V"
echo " - Postgres:     $POSTGRES_V (JDBC Driver)"
echo " - OpenMetadata: $OM_V (Spark Agent)"
echo "-------------------------------------------------------"

echo "▶️  Fetching Kafka Connectors..."
make_dir "connect/clickhouse-sink"
make_dir "connect/msk-datagen"
make_dir "connect/debezium-postgres"
make_dir "connect/redis"
make_dir "connect/iceberg-sink"

CH_URL=$(curl -s https://api.github.com/repos/ClickHouse/clickhouse-kafka-connect/releases/latest | grep -Eo '"browser_download_url":\s*"[^"]+\.zip"' | head -1 | awk -F'"' '{print $4}' || true)
fetch_artifact "ch.zip" "$CH_URL"
[ "$DRY_RUN" -eq 0 ] && unzip -qq ch.zip -d connect/clickhouse-sink && rm ch.zip

MSK_URL=$(curl -s https://api.github.com/repos/awslabs/amazon-msk-data-generator/releases/latest | grep -Eo '"browser_download_url":\s*"[^"]+-dependencies\.jar"' | head -1 | awk -F'"' '{print $4}' || true)
fetch_artifact "connect/msk-datagen/msk-generator.jar" "$MSK_URL"

REDIS_URL=$(curl -s https://api.github.com/repos/redis-field-engineering/redis-kafka-connect/releases/latest | grep -Eo '"browser_download_url":\s*"[^"]+\.zip"' | head -1 | awk -F'"' '{print $4}' || true)
fetch_artifact "redis.zip" "$REDIS_URL"
[ "$DRY_RUN" -eq 0 ] && unzip -qq redis.zip -d connect/redis && rm redis.zip

# Databricks Iceberg Sink
fetch_artifact "iceberg-sink.zip" "$ICEBERG_KC_URL"
[ "$DRY_RUN" -eq 0 ] && unzip -qq iceberg-sink.zip -d connect/iceberg-sink && rm iceberg-sink.zip

# Debezium & OpenLineage Core
fetch_artifact "deb.tar.gz" "https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/${DEB_V}/debezium-connector-postgres-${DEB_V}-plugin.tar.gz"
[ "$DRY_RUN" -eq 0 ] && tar -xzf deb.tar.gz -C connect/debezium-postgres --strip-components=1 && rm deb.tar.gz
fetch_artifact "ol.tar.gz" "https://repo1.maven.org/maven2/io/debezium/debezium-openlineage-core/${DEB_V}/debezium-openlineage-core-${DEB_V}-libs.tar.gz"
[ "$DRY_RUN" -eq 0 ] && tar -xzf ol.tar.gz -C connect/debezium-postgres && rm ol.tar.gz

echo "▶️  Fetching Flink Dependencies for ${FLINK_MINOR}..."
make_dir "flink/1.x"
fetch_artifact "flink/1.x/iceberg-runtime.jar" "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-flink-runtime-${FLINK_MINOR}/${ICEBERG_V}/iceberg-flink-runtime-${FLINK_MINOR}-${ICEBERG_V}.jar"
K_V=$(get_maven_version "org/apache/flink/flink-sql-connector-kafka" "[0-9]+\.[0-9]+\.[0-9]+-${FLINK_MINOR}")
fetch_artifact "flink/1.x/kafka.jar" "https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/${K_V}/flink-sql-connector-kafka-${K_V}.jar"
J_V=$(get_maven_version "org/apache/flink/flink-connector-jdbc" "[0-9]+\.[0-9]+\.[0-9]+-${FLINK_MINOR}")
fetch_artifact "flink/1.x/jdbc.jar" "https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/${J_V}/flink-connector-jdbc-${J_V}.jar"
F_V=$(get_maven_version "org/apache/fluss/fluss-flink-${FLINK_MINOR}" "[0-9]+\.[0-9]+\.[0-9]+(-incubating)?")
fetch_artifact "flink/1.x/fluss.jar" "https://repo1.maven.org/maven2/org/apache/fluss/fluss-flink-${FLINK_MINOR}/${F_V}/fluss-flink-${FLINK_MINOR}-${F_V}.jar"

echo "▶️  Fetching Spark Dependencies..."
make_dir "spark"
ICE_SPARK_ART="iceberg-spark-runtime-${SPARK_COMPAT_MINOR}_${SCALA_V}"
fetch_artifact "spark/iceberg-runtime.jar" "https://repo1.maven.org/maven2/org/apache/iceberg/${ICE_SPARK_ART}/${ICEBERG_V}/${ICE_SPARK_ART}-${ICEBERG_V}.jar"
fetch_artifact "spark/openlineage.jar" "https://repo1.maven.org/maven2/io/openlineage/openlineage-spark_${SCALA_V}/${OL_SPARK_V}/openlineage-spark_${SCALA_V}-${OL_SPARK_V}.jar"
fetch_artifact "spark/openmetadata-agent.jar" "$OM_SPARK_URL"

echo "▶️  Fetching Shared Iceberg Dependencies..."
make_dir "shared"
fetch_artifact "shared/iceberg-aws-bundle.jar" "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_V}/iceberg-aws-bundle-${ICEBERG_V}.jar"
fetch_artifact "shared/postgresql.jar" "https://repo1.maven.org/maven2/org/postgresql/postgresql/${POSTGRES_V}/postgresql-${POSTGRES_V}.jar"

echo "✅ Script execution complete!"
