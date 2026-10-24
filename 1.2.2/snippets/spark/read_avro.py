import json
import urllib.request

from pyspark.sql import SparkSession
from pyspark.sql.avro.functions import from_avro
from pyspark.sql.functions import expr

spark = SparkSession.builder.appName("read-avro").getOrCreate()

# The latest schema of the subject, as the schema registry holds it.
url = "http://karapace:8081/subjects/orders-value/versions/latest"
with urllib.request.urlopen(url, timeout=30) as reply:
    schema = json.load(reply)["schema"]

raw = (
    spark.read.format("kafka")
    .option("kafka.bootstrap.servers", "broker-1:19092")
    .option("subscribe", "orders")
    .load()
)

# Skip the first 5 bytes of each value: a zero byte and the 4-byte schema id.
orders = raw.select(
    from_avro(expr("substring(value, 6, length(value) - 5)"), schema).alias("order")
).select("order.*")
orders.orderBy("supplier", "price").show()
