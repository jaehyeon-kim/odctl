from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("spark-orders").getOrCreate()

spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.demo")
spark.sql("""
  CREATE OR REPLACE TABLE iceberg.demo.raw_orders (supplier STRING, price DOUBLE)
  USING iceberg""")
spark.sql("""
  INSERT INTO iceberg.demo.raw_orders VALUES ('a', 5.0), ('a', 10.0), ('b', 7.5)""")
spark.sql("""
  CREATE OR REPLACE TABLE iceberg.demo.daily_orders (supplier STRING, total DOUBLE)
  USING iceberg""")
spark.sql("""
  INSERT INTO iceberg.demo.daily_orders
  SELECT supplier, sum(price) FROM iceberg.demo.raw_orders GROUP BY supplier""")
