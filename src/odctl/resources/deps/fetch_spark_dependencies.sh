#!/bin/bash
set -eo pipefail

DRY_RUN=0
if [[ "$1" == "dry-run" || "$1" == "--dry-run" ]]; then DRY_RUN=1; echo "⚠️  Running in DRY-RUN mode."; fi

make_dir() { if [ "$DRY_RUN" -eq 0 ]; then mkdir -p "$1"; fi; }
fetch_artifact() {
    if [ "$DRY_RUN" -eq 1 ]; then echo " 🔍 Checking: $2"; curl -sL -I -f "$2" > /dev/null || exit 1;
    else echo " ⬇️  Downloading: $2"; curl -sL -f -o "$1" "$2"; fi
}
# Versions come from versions.env so a bump is one edit rather than several
# kept in step. See issue #5.
# shellcheck source=versions.env
. "$(dirname "$0")/versions.env"

get_maven_version() {
    curl -sL "https://repo1.maven.org/maven2/${1}/maven-metadata.xml" | grep -Eo "<version>${2}</version>" | sort -V | tail -1 | sed -E 's#</?version>##g' || true
}

echo "▶️  Resolving Spark Versions..."
SCALA_V="2.13"

# 🔒 HARDCODED: Lock to Spark 4.1.x; Iceberg comes from versions.env
SPARK_COMPAT_MINOR="4.1"

# Keep OpenLineage dynamic as it relies on frequent patch updates
OL_SPARK_V=$(get_maven_version "io/openlineage/openlineage-spark_${SCALA_V}" "[0-9]+\.[0-9]+\.[0-9]+")
if [ -z "$OL_SPARK_V" ]; then echo "❌ Error: Could not resolve OpenLineage Spark version!"; exit 1; fi

# Fetch OpenMetadata via GitHub API (Note: Subject to 60 req/hr rate limits unauthenticated)
OM_JSON=$(curl -sL https://api.github.com/repos/open-metadata/openmetadata-spark-agent/releases/latest)
OM_SPARK_URL=$(echo "$OM_JSON" | grep -Eo '"browser_download_url":\s*"[^"]+\.jar"' | head -1 | awk -F'"' '{print $4}' || true)
if [ -z "$OM_SPARK_URL" ]; then echo "❌ Error: Could not resolve OpenMetadata Spark Agent JAR URL! (Check GitHub rate limits)"; exit 1; fi

echo "▶️  Fetching Spark Dependencies..."
make_dir "spark"
ICE_SPARK_ART="iceberg-spark-runtime-${SPARK_COMPAT_MINOR}_${SCALA_V}"

fetch_artifact "spark/iceberg-runtime.jar" "https://repo1.maven.org/maven2/org/apache/iceberg/${ICE_SPARK_ART}/${ICEBERG_V}/${ICE_SPARK_ART}-${ICEBERG_V}.jar"
fetch_artifact "spark/openlineage.jar" "https://repo1.maven.org/maven2/io/openlineage/openlineage-spark_${SCALA_V}/${OL_SPARK_V}/openlineage-spark_${SCALA_V}-${OL_SPARK_V}.jar"
fetch_artifact "spark/openmetadata-agent.jar" "$OM_SPARK_URL"

# Hadoop S3A, so the Iceberg procedures that walk storage through Hadoop's
# FileSystem API work against SeaweedFS. S3FileIO covers the data path already;
# these two jars are what remove_orphan_files and add_files need.
fetch_artifact "spark/hadoop-aws.jar" "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_V}/hadoop-aws-${HADOOP_AWS_V}.jar"
fetch_artifact "spark/aws-sdk-bundle.jar" "https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/${AWS_SDK_V}/bundle-${AWS_SDK_V}.jar"

echo "✅ Spark dependencies complete!"
