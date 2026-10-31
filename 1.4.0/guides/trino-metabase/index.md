# Trino and Metabase

The `trino` profile runs Trino, which queries PostgreSQL, Iceberg, ClickHouse, Kafka and Valkey through one SQL interface. The `metabase` profile runs Metabase, which draws charts and dashboards over those databases. Metabase keeps its own settings and dashboards in PostgreSQL, so both profiles start `postgres`. The end-to-end tests run the commands below on every release.

This guide builds on [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/index.md). The catalogs read the services of earlier guides, such as [Kafka](https://jaehyeon.me/odctl/latest/guides/kafka/index.md), [Ingest into Iceberg](https://jaehyeon.me/odctl/latest/guides/iceberg-ingestion/index.md) and [ClickHouse](https://jaehyeon.me/odctl/latest/guides/clickhouse/index.md), when their profiles are running. Start both profiles:

```bash
odctl up trino metabase
```

| Endpoint                        | Address                 |
| ------------------------------- | ----------------------- |
| Trino UI and JDBC from the host | `http://127.0.0.1:8080` |
| Metabase from the host          | `http://127.0.0.1:3000` |

## Trino Catalogs

A Trino catalog is a configured connection to one data source. This lists them:

```bash
docker exec trino trino --execute "SHOW CATALOGS"
```

The command prints `"clickhouse"`, `"iceberg"`, `"kafka"`, `"postgres"`, `"system"` and `"valkey"`, one per line, with a `Picked up JAVA_TOOL_OPTIONS` line before them:

| Catalog      | Reads                                                 | Needs                        |
| ------------ | ----------------------------------------------------- | ---------------------------- |
| `postgres`   | the `odctl` database                                  | nothing more                 |
| `iceberg`    | tables in the REST catalog, with files on SeaweedFS   | `catalog`                    |
| `clickhouse` | the `feature_store` database on `ch-11`               | `ch-lite` or `ch-full`       |
| `kafka`      | topics, with fields from the Karapace schema registry | `kafka-lite` or `kafka-full` |
| `valkey`     | keys in Valkey                                        | `valkey`                     |

Every catalog loads when Trino starts, even when its service is not running. A query against such a catalog fails until you start that profile. Catalogs finish loading after Trino's health endpoint starts answering, so `SHOW CATALOGS` can take a minute to list them all.

This runs a query with no table:

```bash
docker exec trino trino --execute "SELECT 1"
```

It prints `"1"`. Trino has no password authentication, so it accepts any user name. `docker exec -it trino trino` connects as `trino`. Pass `--user user` to use the name the rest of the stack uses. [Trino Access Rules](https://jaehyeon.me/odctl/latest/how-it-works/#trino-access-rules) explains the rules in `trino/rules.json`.

The Trino UI at `http://127.0.0.1:8080` asks only for a user name. It shows the cluster and the queries that ran in the last few minutes.

## Metabase

Open `http://127.0.0.1:3000` and create the first admin account. Then add each database under Admin settings, Databases, with these settings:

| Database type         | Host       | Port   | Other settings                                                  |
| --------------------- | ---------- | ------ | --------------------------------------------------------------- |
| PostgreSQL            | `postgres` | `5432` | database `odctl`, user `user`, password `password`              |
| ClickHouse            | `ch-11`    | `8123` | database `default`, user `default`, password `password`, no SSL |
| Starburst (for Trino) | `trino`    | `8080` | catalog `postgres`, schema `public`, user `admin`, no SSL       |

Metabase runs inside the `odctl` network, so it reaches each database by container name. Use the Starburst driver for Trino, because it is the Trino driver Metabase ships. It needs a catalog, and any catalog in the table above works.

Metabase takes a while to start. It is ready when this request answers `{"status":"ok"}`:

```bash
curl http://127.0.0.1:3000/api/health
```

A SQL question on the PostgreSQL connection, shown as a bar chart:

## From Another Container

Inside the [`odctl` network](https://jaehyeon.me/odctl/latest/how-it-works/#how-you-reach-a-service), Trino is at `http://trino:8080` and Metabase at `http://metabase:3000`.

## Runnable Example

Save this file as `example.sh` and run it with `bash example.sh` in the folder that holds your `.odctl` workspace. It waits for the catalogs and for Metabase before it runs the commands above:

```bash
#!/usr/bin/env bash
# Starts trino and metabase, waits until every Trino catalog has loaded and
# Metabase answers, then lists the catalogs and runs a query.
set -euo pipefail

odctl up trino metabase

# Catalogs finish loading after Trino's health endpoint answers.
until docker exec trino trino --execute "SHOW CATALOGS" 2>/dev/null | grep '"valkey"' >/dev/null; do sleep 5; done
docker exec trino trino --execute "SHOW CATALOGS"
docker exec trino trino --execute "SELECT 1"

until curl -fs http://127.0.0.1:3000/api/health; do sleep 5; done
echo
```

It prints the six catalogs, `"1"` and `{"status":"ok"}`.
