# Analytics

## ClickHouse

Profiles: `ch-lite`, `ch-full`. Stack `analytics`, defined in `compose-analytics.yml`.

### ch-lite

Depends on: `deps`. `odctl up ch-lite` also starts: `deps`.

```text
• ClickHouse HTTP (Shard 1 / Replica 1 & 2):
  * External (host): http://127.0.0.1:8123, http://127.0.0.1:8124
  * Internal (Docker): http://ch-11:8123, http://ch-12:8123
```

| Service          | Image                                       | Host:container ports     | Memory limit |
| ---------------- | ------------------------------------------- | ------------------------ | ------------ |
| `ch-keeper`      | `clickhouse/clickhouse-keeper:25.12-alpine` | `9181:9181`              | `512m`       |
| `ch-shard2-stub` | `alpine:3.24`                               | none                     | `64m`        |
| `ch-11`          | `clickhouse/clickhouse-server:25.12-alpine` | `8123:8123`, `9000:9000` | `4g`         |
| `ch-12`          | `clickhouse/clickhouse-server:25.12-alpine` | `8124:8123`, `9001:9000` | `4g`         |

### ch-full

Depends on: `deps`. `odctl up ch-full` also starts: `deps`.

```text
• ClickHouse HTTP (Shards 1 & 2 / Replicas 1 & 2):
  * External (host): http://127.0.0.1:8123, http://127.0.0.1:8124, http://127.0.0.1:8125, http://127.0.0.1:8126
  * Internal (Docker): http://ch-11:8123, http://ch-12:8123, http://ch-21:8123, http://ch-22:8123
```

| Service      | Image                                       | Host:container ports     | Memory limit |
| ------------ | ------------------------------------------- | ------------------------ | ------------ |
| `ch-keeper`  | `clickhouse/clickhouse-keeper:25.12-alpine` | `9181:9181`              | `512m`       |
| `ch-11-full` | `clickhouse/clickhouse-server:25.12-alpine` | `8123:8123`, `9000:9000` | `4g`         |
| `ch-12-full` | `clickhouse/clickhouse-server:25.12-alpine` | `8124:8123`, `9001:9000` | `4g`         |
| `ch-21`      | `clickhouse/clickhouse-server:25.12-alpine` | `8125:8123`, `9002:9000` | `4g`         |
| `ch-22`      | `clickhouse/clickhouse-server:25.12-alpine` | `8126:8123`, `9003:9000` | `4g`         |

## Trino

Profiles: `trino`. Stack `analytics`, defined in `compose-analytics.yml`.

### trino

Depends on: `postgres`. `odctl up trino` also starts: `deps`, `postgres`.

```text
• Trino UI & JDBC connection (no password: no authenticator is
  configured, so any username is accepted):
  * External (host): http://127.0.0.1:8080
  * Internal (Docker): http://trino:8080
• Identities: `docker exec -it trino trino` connects as `trino`, the
  CLI default. Pass `--user user` for the stack-wide convention, or
  `--user analyst`, which trino/rules.json denies schema ownership
  while leaving every table privilege in place.
• Catalogs: postgres works with the trino profile alone. iceberg,
  kafka, clickhouse and valkey load without their backing services,
  so they appear in SHOW CATALOGS and then fail at query time unless
  catalog, storage, kafka-lite, ch-lite or valkey is also up.
```

| Service | Image               | Host:container ports | Memory limit |
| ------- | ------------------- | -------------------- | ------------ |
| `trino` | `trinodb/trino:484` | `8080:8080`          | `4g`         |

## Metabase

Profiles: `metabase`. Stack `analytics`, defined in `compose-analytics.yml`.

### metabase

Depends on: `postgres`. `odctl up metabase` also starts: `deps`, `postgres`.

```text
• Metabase Dashboard Engine:
  * External (host): http://127.0.0.1:3000
  * Internal (Docker): http://metabase:3000
```

| Service    | Image                         | Host:container ports | Memory limit |
| ---------- | ----------------------------- | -------------------- | ------------ |
| `metabase` | `metabase/metabase:v0.64.3.1` | `3000:3000`          | `1500m`      |
