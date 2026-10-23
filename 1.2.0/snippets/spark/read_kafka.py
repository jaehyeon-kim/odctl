from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("read-kafka").getOrCreate()

df = (
    spark.read.format("kafka")
    .option("kafka.bootstrap.servers", "broker-1:19092")
    .option("subscribe", "spark-demo")
    .load()
)
df.selectExpr("CAST(value AS STRING) AS value").orderBy("value").show(truncate=False)
