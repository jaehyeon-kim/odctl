#!/bin/bash
set -e

DRY_RUN=0
if [[ "$1" == "dry-run" || "$1" == "--dry-run" ]]; then
    DRY_RUN=1
    echo "⚠️  Running in DRY-RUN mode. Validating Aiven repositories only."
fi

get_latest_tag() {
    local repo=$1
    curl -s "https://api.github.com/repos/${repo}/releases/latest" | \
        grep -Eo '"tag_name":\s*"[^"]+"' | head -1 | awk -F'"' '{print $4}' || true
}

build_repo() {
    local name=$1
    local repo_url=$2
    local tag=$3
    local build_cmd=$4

    echo "▶️  Processing $name..."
    if [ -z "$tag" ]; then echo "    ❌ Error resolving tag for $name"; exit 1; fi

    if [ "$DRY_RUN" -eq 1 ]; then
        echo "    ✅ Found Latest Tag: $tag"
        git ls-remote --tags "$repo_url" "$tag" > /dev/null
    else
        git clone --branch "$tag" --depth 1 "$repo_url" "$name"
        cd "$name"
        eval "$build_cmd"
        cd ..
    fi
}

echo "▶️  Resolving latest stable Aiven source versions..."

JDBC_TAG=$(get_latest_tag "Aiven-Open/jdbc-connector-for-apache-kafka")
S3_TAG=$(get_latest_tag "Aiven-Open/cloud-storage-connectors-for-apache-kafka")

# Build Aiven JDBC
build_repo "aiven-jdbc" \
    "https://github.com/Aiven-Open/jdbc-connector-for-apache-kafka.git" \
    "$JDBC_TAG" \
    "./gradlew clean assemble"

# Build Aiven S3
build_repo "aiven-s3" \
    "https://github.com/Aiven-Open/cloud-storage-connectors-for-apache-kafka.git" \
    "$S3_TAG" \
    "./gradlew clean assemble"

echo "✅ Script execution complete!"
