#!/bin/bash
set -e

DRY_RUN=0
if [[ "$1" == "dry-run" || "$1" == "--dry-run" ]]; then DRY_RUN=1; echo "⚠️ Running in DRY-RUN mode."; fi

make_dir() { if [ "$DRY_RUN" -eq 0 ]; then mkdir -p "$1"; fi; }
fetch_artifact() {
    if [ "$DRY_RUN" -eq 1 ]; then echo " 🔍 Checking: $2"; curl -sL -I -f "$2" > /dev/null || exit 1;
    else echo " ⬇️  Downloading: $(basename $1)"; curl -sL -f -o "$1" "$2"; fi
}

echo "▶️ Loading Pinned Versions (Reproducible Build Mode)..."
# -------------------------------------------------------------------
# 📦 PINNED VERSIONS (Ensures stability and prevents runtime mismatch)
# -------------------------------------------------------------------
CONFLUENT_V="7.6.1"
AVRO_V="1.11.3"
PROTOBUF_V="3.25.3"
JACKSON_V="2.16.1"
GUAVA_V="33.1.0-jre"
FAILUREACCESS_V="1.0.2"
HTTPCLIENT_V="5.2.3"
SLF4J_V="2.0.12"
COMPRESS_V="1.26.1"
XZ_V="1.9"
PARANAMER_V="2.8"
EVERIT_V="1.14.4"
ORG_JSON_V="20240303"
JAXRS_V="3.1.0"

make_dir "shared/confluent-converters"
CONFLUENT_MAVEN="https://packages.confluent.io/maven/io/confluent"
MAVEN_CENTRAL="https://repo1.maven.org/maven2"

# -------------------------------------------------------------------
# 1. CORE LAYER (Schema Registry Client & Utils)
# -------------------------------------------------------------------
echo "▶️ Fetching Confluent Core..."
fetch_artifact "shared/confluent-converters/kafka-schema-registry-client.jar" "${CONFLUENT_MAVEN}/kafka-schema-registry-client/${CONFLUENT_V}/kafka-schema-registry-client-${CONFLUENT_V}.jar"
fetch_artifact "shared/confluent-converters/common-config.jar" "${CONFLUENT_MAVEN}/common-config/${CONFLUENT_V}/common-config-${CONFLUENT_V}.jar"
fetch_artifact "shared/confluent-converters/common-utils.jar" "${CONFLUENT_MAVEN}/common-utils/${CONFLUENT_V}/common-utils-${CONFLUENT_V}.jar"

# ---> FIX: Add ONLY the 2 base jars required by AvroConverter. 
# Do NOT add kafka-schema-rules.jar, as that triggers the ProtobufModule crash.
fetch_artifact "shared/confluent-converters/kafka-schema-serializer.jar" "${CONFLUENT_MAVEN}/kafka-schema-serializer/${CONFLUENT_V}/kafka-schema-serializer-${CONFLUENT_V}.jar"
fetch_artifact "shared/confluent-converters/kafka-schema-converter.jar" "${CONFLUENT_MAVEN}/kafka-schema-converter/${CONFLUENT_V}/kafka-schema-converter-${CONFLUENT_V}.jar"

# -------------------------------------------------------------------
# 2. SYSTEM WIDE (Shared Transitives)
# -------------------------------------------------------------------
echo "▶️ Fetching System-Wide Dependencies..."
# Jackson (Critical for JSON Schema and general serialization)
fetch_artifact "shared/confluent-converters/jackson-databind.jar" "${MAVEN_CENTRAL}/com/fasterxml/jackson/core/jackson-databind/${JACKSON_V}/jackson-databind-${JACKSON_V}.jar"
fetch_artifact "shared/confluent-converters/jackson-core.jar" "${MAVEN_CENTRAL}/com/fasterxml/jackson/core/jackson-core/${JACKSON_V}/jackson-core-${JACKSON_V}.jar"
fetch_artifact "shared/confluent-converters/jackson-annotations.jar" "${MAVEN_CENTRAL}/com/fasterxml/jackson/core/jackson-annotations/${JACKSON_V}/jackson-annotations-${JACKSON_V}.jar"
# HTTP Client & API
fetch_artifact "shared/confluent-converters/httpclient5.jar" "${MAVEN_CENTRAL}/org/apache/httpcomponents/client5/httpclient5/${HTTPCLIENT_V}/httpclient5-${HTTPCLIENT_V}.jar"
fetch_artifact "shared/confluent-converters/httpcore5.jar" "${MAVEN_CENTRAL}/org/apache/httpcomponents/core5/httpcore5/${HTTPCLIENT_V}/httpcore5-${HTTPCLIENT_V}.jar"
fetch_artifact "shared/confluent-converters/jakarta.ws.rs-api.jar" "${MAVEN_CENTRAL}/jakarta/ws/rs/jakarta.ws.rs-api/${JAXRS_V}/jakarta.ws.rs-api-${JAXRS_V}.jar"
# Guava
fetch_artifact "shared/confluent-converters/guava.jar" "${MAVEN_CENTRAL}/com/google/guava/guava/${GUAVA_V}/guava-${GUAVA_V}.jar"
fetch_artifact "shared/confluent-converters/failureaccess.jar" "${MAVEN_CENTRAL}/com/google/guava/failureaccess/${FAILUREACCESS_V}/failureaccess-${FAILUREACCESS_V}.jar"
# Logging
fetch_artifact "shared/confluent-converters/slf4j-api.jar" "${MAVEN_CENTRAL}/org/slf4j/slf4j-api/${SLF4J_V}/slf4j-api-${SLF4J_V}.jar"

# -------------------------------------------------------------------
# 3. AVRO ECOSYSTEM
# -------------------------------------------------------------------
echo "▶️ Fetching Avro Ecosystem..."
fetch_artifact "shared/confluent-converters/kafka-connect-avro-converter.jar" "${CONFLUENT_MAVEN}/kafka-connect-avro-converter/${CONFLUENT_V}/kafka-connect-avro-converter-${CONFLUENT_V}.jar"
fetch_artifact "shared/confluent-converters/kafka-connect-avro-data.jar" "${CONFLUENT_MAVEN}/kafka-connect-avro-data/${CONFLUENT_V}/kafka-connect-avro-data-${CONFLUENT_V}.jar"
fetch_artifact "shared/confluent-converters/kafka-avro-serializer.jar" "${CONFLUENT_MAVEN}/kafka-avro-serializer/${CONFLUENT_V}/kafka-avro-serializer-${CONFLUENT_V}.jar"
fetch_artifact "shared/confluent-converters/avro.jar" "${MAVEN_CENTRAL}/org/apache/avro/avro/${AVRO_V}/avro-${AVRO_V}.jar"
# Avro Safety Net Transitives
fetch_artifact "shared/confluent-converters/commons-compress.jar" "${MAVEN_CENTRAL}/org/apache/commons/commons-compress/${COMPRESS_V}/commons-compress-${COMPRESS_V}.jar"
fetch_artifact "shared/confluent-converters/xz.jar" "${MAVEN_CENTRAL}/org/tukaani/xz/${XZ_V}/xz-${XZ_V}.jar"
fetch_artifact "shared/confluent-converters/paranamer.jar" "${MAVEN_CENTRAL}/com/thoughtworks/paranamer/paranamer/${PARANAMER_V}/paranamer-${PARANAMER_V}.jar"

# -------------------------------------------------------------------
# 4. PROTOBUF ECOSYSTEM
# -------------------------------------------------------------------
echo "▶️ Fetching Protobuf Ecosystem..."
fetch_artifact "shared/confluent-converters/kafka-connect-protobuf-converter.jar" "${CONFLUENT_MAVEN}/kafka-connect-protobuf-converter/${CONFLUENT_V}/kafka-connect-protobuf-converter-${CONFLUENT_V}.jar"
fetch_artifact "shared/confluent-converters/kafka-protobuf-provider.jar" "${CONFLUENT_MAVEN}/kafka-protobuf-provider/${CONFLUENT_V}/kafka-protobuf-provider-${CONFLUENT_V}.jar"
fetch_artifact "shared/confluent-converters/kafka-protobuf-serializer.jar" "${CONFLUENT_MAVEN}/kafka-protobuf-serializer/${CONFLUENT_V}/kafka-protobuf-serializer-${CONFLUENT_V}.jar"
# Protobuf Transitives
fetch_artifact "shared/confluent-converters/protobuf-java.jar" "${MAVEN_CENTRAL}/com/google/protobuf/protobuf-java/${PROTOBUF_V}/protobuf-java-${PROTOBUF_V}.jar"
fetch_artifact "shared/confluent-converters/protobuf-java-util.jar" "${MAVEN_CENTRAL}/com/google/protobuf/protobuf-java-util/${PROTOBUF_V}/protobuf-java-util-${PROTOBUF_V}.jar"

# -------------------------------------------------------------------
# 5. JSON SCHEMA ECOSYSTEM
# -------------------------------------------------------------------
echo "▶️ Fetching JSON Schema Ecosystem..."
fetch_artifact "shared/confluent-converters/kafka-connect-json-schema-converter.jar" "${CONFLUENT_MAVEN}/kafka-connect-json-schema-converter/${CONFLUENT_V}/kafka-connect-json-schema-converter-${CONFLUENT_V}.jar"
fetch_artifact "shared/confluent-converters/kafka-json-schema-provider.jar" "${CONFLUENT_MAVEN}/kafka-json-schema-provider/${CONFLUENT_V}/kafka-json-schema-provider-${CONFLUENT_V}.jar"
fetch_artifact "shared/confluent-converters/kafka-json-schema-serializer.jar" "${CONFLUENT_MAVEN}/kafka-json-schema-serializer/${CONFLUENT_V}/kafka-json-schema-serializer-${CONFLUENT_V}.jar"
# JSON Transitives (Relies heavily on Jackson downloaded above)
fetch_artifact "shared/confluent-converters/everit-json-schema.jar" "${MAVEN_CENTRAL}/com/github/erosb/everit-json-schema/${EVERIT_V}/everit-json-schema-${EVERIT_V}.jar"
fetch_artifact "shared/confluent-converters/json.jar" "${MAVEN_CENTRAL}/org/json/json/${ORG_JSON_V}/json-${ORG_JSON_V}.jar"

echo "✅ Schema dependencies complete!"
