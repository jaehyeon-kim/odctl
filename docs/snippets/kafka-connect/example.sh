#!/usr/bin/env bash
# Starts kafka-lite, registers a data generator connector, reads three of its
# records, prints the connector's status and removes it.
set -euo pipefail

odctl up kafka-lite

# The REST API answers a little after the worker starts.
until curl -fs http://127.0.0.1:8083/connectors >/dev/null; do sleep 2; done

curl -s -X POST -H 'Content-Type: application/json' http://127.0.0.1:8083/connectors -d @- <<'JSON'
{
  "name": "demo-datagen",
  "config": {
    "connector.class": "com.amazonaws.mskdatagen.GeneratorSourceConnector",
    "tasks.max": "1",
    "genkp.customers.with": "#{Code.isbn10}",
    "genv.customers.name.with": "#{Name.first_name}",
    "genv.customers.visits.with": "#{number.number_between '1','10'}",
    "global.throttle.ms": "500",
    "key.converter": "org.apache.kafka.connect.storage.StringConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": "false"
  }
}
JSON
echo

docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server broker-1:19092 \
  --topic customers --from-beginning --max-messages 3 --timeout-ms 60000 \
  --formatter-property print.key=true

curl -s http://127.0.0.1:8083/connectors/demo-datagen/status
echo
curl -s -X DELETE http://127.0.0.1:8083/connectors/demo-datagen
