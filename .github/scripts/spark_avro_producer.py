"""Write the Flink SQL guide's orders to Kafka as Avro, for the Spark Avro check.

Runs in the karapace container: docker exec -i karapace python3 - < this file.
It registers the schema that Flink's avro-confluent format registers for the
orders table, under the subject orders-value, and writes the three records
that the Flink SQL guide inserts.
"""

import io
import json
import struct

import avro.schema
import requests
from avro.io import BinaryEncoder, DatumWriter
from confluent_kafka import Producer

REGISTRY = "http://localhost:8081"
SUBJECT = "orders-value"
SCHEMA = {
    "type": "record",
    "name": "record",
    "namespace": "org.apache.flink.avro.generated",
    "fields": [
        {"name": "supplier", "type": ["null", "string"], "default": None},
        {"name": "price", "type": ["null", "double"], "default": None},
    ],
}

# Register the schema. Karapace answers with the schema id, and the same id if
# the schema is already registered.
reply = requests.post(
    f"{REGISTRY}/subjects/{SUBJECT}/versions",
    json={"schema": json.dumps(SCHEMA)},
    timeout=30,
)
reply.raise_for_status()
schema_id = reply.json()["id"]

# Each value is a zero byte, the schema id as 4 bytes and the Avro binary record.
writer = DatumWriter(avro.schema.parse(json.dumps(SCHEMA)))
producer = Producer({"bootstrap.servers": "broker-1:19092"})
for supplier, price in [("a", 10.0), ("a", 5.0), ("b", 7.5)]:
    buffer = io.BytesIO()
    buffer.write(struct.pack(">bI", 0, schema_id))
    writer.write({"supplier": supplier, "price": price}, BinaryEncoder(buffer))
    producer.produce("orders", buffer.getvalue())
producer.flush()
