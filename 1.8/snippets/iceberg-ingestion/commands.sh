# Commands from docs/guides/iceberg-ingestion.md. .github/scripts/smoke.sh runs
# the Kafka Connect sections, the register section from this folder, where
# demo-iceberg.json is; the Flink SQL statements are in steps.sql.

# smoke.sh does not run the up sections, because the e2e workflow starts
# each profile itself; they are the commands as the page shows them.
# --8<-- [start:up]
odctl up kafka-lite catalog
# --8<-- [end:up]

# --8<-- [start:create-table]
api=http://127.0.0.1:8181/v1/namespaces
curl -X POST -H 'Content-Type: application/json' -d '{"namespace":["demo"]}' "$api"
curl -X POST -H 'Content-Type: application/json' \
  -d '{"name":"kc","schema":{"type":"struct","schema-id":0,"fields":[{"id":1,"name":"id","required":false,"type":"long"},{"id":2,"name":"name","required":false,"type":"string"}]}}' \
  "$api/demo/tables"
# --8<-- [end:create-table]

# --8<-- [start:topics-produce]
for topic in demo-iceberg control-iceberg; do
  docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server broker-1:19092 \
    --create --if-not-exists --topic "$topic" --partitions 1 --replication-factor 1
done
for i in 1 2 3 4 5; do echo "{\"id\":$i,\"name\":\"n$i\"}"; done | docker exec -i kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server broker-1:19092 --topic demo-iceberg
# --8<-- [end:topics-produce]

# --8<-- [start:register]
curl -X POST -H 'Content-Type: application/json' \
  http://127.0.0.1:8083/connectors -d @demo-iceberg.json
# --8<-- [end:register]

# --8<-- [start:records]
curl -s http://127.0.0.1:8181/v1/namespaces/demo/tables/kc | grep -o '"total-records":"[0-9]*"'
# --8<-- [end:records]

# --8<-- [start:status-remove]
curl -s http://127.0.0.1:8083/connectors/demo-iceberg/status
curl -X DELETE http://127.0.0.1:8083/connectors/demo-iceberg
# --8<-- [end:status-remove]

# --8<-- [start:flink-client]
odctl up flink-lite
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
# --8<-- [end:flink-client]
