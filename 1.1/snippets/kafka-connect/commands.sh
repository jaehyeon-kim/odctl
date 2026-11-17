# Commands from docs/guides/kafka-connect.md. .github/scripts/smoke.sh runs each
# section, the register section from this folder, where demo-iceberg.json is.

# --8<-- [start:plugins]
curl -s http://127.0.0.1:8083/connector-plugins
# --8<-- [end:plugins]

# --8<-- [start:register]
curl -X POST -H 'Content-Type: application/json' \
  http://127.0.0.1:8083/connectors -d @demo-iceberg.json
# --8<-- [end:register]

# --8<-- [start:status-remove]
curl -s http://127.0.0.1:8083/connectors/demo-iceberg/status
curl -X DELETE http://127.0.0.1:8083/connectors/demo-iceberg
# --8<-- [end:status-remove]

# --8<-- [start:logs]
docker logs --tail 40 connect
# --8<-- [end:logs]
