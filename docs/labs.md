# Labs

Work in progress. A series of labs takes one generated dataset of web events and logs for five tenants through Kafka, Flink, ClickHouse, Spark, Trino and the MLOps tools, each lab building on the one before. The code will be in [benchtop](https://github.com/jaehyeon-kim/benchtop), and each lab will be listed here as it is published.

![Labs: dynamic-des writes to Kafka; Flink lands it in Iceberg; ClickHouse serves it; Spark and Airflow maintain Iceberg and build features; Trino queries both; Feast, MLflow and Evidently use the features](images/labs.png)

Until then, the [guides](guides/kafka.md) show each technology on its own.
