# Labs

Work in progress. A series of labs takes one generated dataset of web events and logs for five tenants through Kafka, Flink, ClickHouse, Spark, Trino and the MLOps tools, each lab building on the one before. The code will be in [benchtop](https://github.com/jaehyeon-kim/benchtop), and each lab will be listed here as it is published.

![Labs: desflow writes events to Kafka and reference data to PostgreSQL, which Debezium in Kafka Connect also sends to Kafka with Avro schemas in Karapace; Flink lands the events in Iceberg; ClickHouse reads Kafka and Iceberg; Trino queries both; Spark and Airflow maintain Iceberg and build features for Feast, MLflow and Evidently](images/labs.png)

Until then, the [guides](guides/kafka.md) show each technology on its own.
