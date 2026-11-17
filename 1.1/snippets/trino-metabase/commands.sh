# Commands from docs/guides/trino-metabase.md. .github/scripts/smoke.sh runs each section.

# --8<-- [start:catalogs]
docker exec trino trino --execute "SHOW CATALOGS"
# --8<-- [end:catalogs]

# --8<-- [start:query]
docker exec trino trino --execute "SELECT 1"
# --8<-- [end:query]

# --8<-- [start:metabase-health]
curl http://127.0.0.1:3000/api/health
# --8<-- [end:metabase-health]
