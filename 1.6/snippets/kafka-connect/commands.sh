# Commands from docs/guides/kafka-connect.md. .github/scripts/smoke.sh runs each
# section, the register section from this folder, where demo-datagen.json is.

# smoke.sh does not run the up sections, because the e2e workflow starts
# each profile itself; they are the commands as the page shows them.
# --8<-- [start:up]
odctl up kafka-lite
# --8<-- [end:up]

# --8<-- [start:up-postgres]
odctl up postgres kafka-lite
# --8<-- [end:up-postgres]

# --8<-- [start:plugins]
curl -s http://127.0.0.1:8083/connector-plugins
# --8<-- [end:plugins]

# --8<-- [start:register]
curl -X POST -H 'Content-Type: application/json' \
  http://127.0.0.1:8083/connectors -d @demo-datagen.json
# --8<-- [end:register]

# --8<-- [start:read]
docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server broker-1:19092 \
  --topic customers --from-beginning --max-messages 3 --timeout-ms 60000 \
  --formatter-property print.key=true
# --8<-- [end:read]

# --8<-- [start:status-remove]
curl -s http://127.0.0.1:8083/connectors/demo-datagen/status
curl -X DELETE http://127.0.0.1:8083/connectors/demo-datagen
# --8<-- [end:status-remove]

# --8<-- [start:logs]
docker logs --tail 40 connect
# --8<-- [end:logs]
