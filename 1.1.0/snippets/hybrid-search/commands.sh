# Commands from docs/guides/hybrid-search.md. The SQL is in steps.sql, which
# .github/scripts/smoke.sh runs through psql.

# --8<-- [start:psql]
odctl up postgres
docker exec -it postgres psql -U user -d vector
# --8<-- [end:psql]
