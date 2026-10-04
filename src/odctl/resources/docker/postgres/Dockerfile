FROM postgres:18-trixie

# Metadata Bindings for GHCR
LABEL org.opencontainers.image.source="https://github.com/jaehyeon-kim/odctl"
LABEL org.opencontainers.image.description="PostgreSQL 18 for the Open Data Stack, with pgvector for vector search, pg_textsearch for BM25 keyword search and PostGIS for geospatial queries."

# pgvector is compiled at a pinned release, the way pgvector's own image does it,
# because the PostgreSQL apt repository can lag a release behind. A volume made
# with a newer pgvector cannot be moved back to an older one.
ARG PGVECTOR_V=0.8.7
# pg_textsearch publishes a .deb for each PostgreSQL major and architecture.
ARG PG_TEXTSEARCH_V=1.5.1
# Set by BuildKit to amd64 or arm64.
ARG TARGETARCH

RUN set -eux \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential "postgresql-server-dev-${PG_MAJOR}" curl ca-certificates unzip \
        "postgresql-${PG_MAJOR}-postgis-3" \
    && curl -fsSL "https://github.com/pgvector/pgvector/archive/refs/tags/v${PGVECTOR_V}.tar.gz" \
        | tar -xz -C /tmp \
    && make -C "/tmp/pgvector-${PGVECTOR_V}" OPTFLAGS="" \
    && make -C "/tmp/pgvector-${PGVECTOR_V}" install \
    && curl -fsSL -o /tmp/pg_textsearch.zip \
        "https://github.com/timescale/pg_textsearch/releases/download/v${PG_TEXTSEARCH_V}/pg-textsearch-v${PG_TEXTSEARCH_V}-pg${PG_MAJOR}-${TARGETARCH}.zip" \
    && unzip -d /tmp/pg_textsearch /tmp/pg_textsearch.zip \
    && apt-get install -y --no-install-recommends /tmp/pg_textsearch/*.deb \
    && apt-get purge -y --auto-remove build-essential "postgresql-server-dev-${PG_MAJOR}" curl unzip \
    && rm -rf /tmp/pgvector-* /tmp/pg_textsearch* /var/lib/apt/lists/*
