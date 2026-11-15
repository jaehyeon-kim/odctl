import pendulum
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.sdk import DAG

with DAG(
    dag_id="lineage_orders",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
):
    seed_raw_orders = SQLExecuteQueryOperator(
        task_id="seed_raw_orders",
        conn_id="odctl_postgres",
        sql=[
            "DROP TABLE IF EXISTS dev.raw_orders",
            "CREATE TABLE dev.raw_orders AS SELECT * FROM "
            "(VALUES ('a', 5.0), ('a', 10.0), ('b', 7.5)) AS t(supplier, price)",
        ],
    )
    build_daily_orders = SQLExecuteQueryOperator(
        task_id="build_daily_orders",
        conn_id="odctl_postgres",
        sql=[
            "DROP TABLE IF EXISTS dev.daily_orders",
            "CREATE TABLE dev.daily_orders AS "
            "SELECT supplier, sum(price) AS total FROM dev.raw_orders GROUP BY supplier",
        ],
    )
    seed_raw_orders >> build_daily_orders
