# Fluss

Apache Fluss is a streaming storage for real-time analytics: it keeps tables that Flink writes and reads with low latency, either as logs or as tables with a primary key. The `fluss` profile runs a coordinator server, one tablet server and the ZooKeeper they register in. Flink reads and writes Fluss tables through the Fluss catalog, whose client jar comes from the shared volume that the `deps` profile fills. The end-to-end tests run the commands below on every release.

This guide builds on [Flink SQL](https://jaehyeon.me/odctl/latest/guides/flink-sql/index.md), which opens the SQL client. Start both profiles:

```bash
odctl up fluss flink-lite
```

| Endpoint                                 | Address                  |
| ---------------------------------------- | ------------------------ |
| Coordinator inside the `odctl` network   | `fluss-coordinator:9123` |
| Tablet server inside the `odctl` network | `fluss-tablet-1:9123`    |

The coordinator is also published on `127.0.0.1:9123` and the tablet server on `127.0.0.1:9124`. Both advertise their container names, which resolve only inside the `odctl` network, so run Fluss clients in a container, such as Flink.

## Check the Cluster Formed

The servers register in ZooKeeper once they are up. This lists the tablet servers and reads the active coordinator:

```bash
docker exec fluss-zookeeper zkCli.sh -server localhost:2181 ls /fluss/tabletservers/ids
docker exec fluss-zookeeper zkCli.sh -server localhost:2181 get /fluss/coordinators/active
```

Among the ZooKeeper client's log lines, the first command prints `[0]`, the id of the one tablet server. The second prints a JSON object whose `listeners` include `CLIENT://fluss-coordinator:9123`.

## Write and Read a Table with Flink SQL

Open the SQL client in the JobManager container:

```bash
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
```

Run these statements in the client. They register the Fluss catalog, create a table with a primary key, write three rows and read them back:

```sql
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';
SET 'sql-client.execution.result-mode' = 'tableau';
CREATE CATALOG fluss_catalog WITH ('type' = 'fluss', 'bootstrap.servers' = 'fluss-coordinator:9123');
CREATE DATABASE IF NOT EXISTS fluss_catalog.demo;
CREATE TABLE fluss_catalog.demo.t (id BIGINT, name STRING, PRIMARY KEY (id) NOT ENFORCED);
INSERT INTO fluss_catalog.demo.t VALUES (1, 'a'), (2, 'b'), (3, 'c');
SELECT * FROM fluss_catalog.demo.t LIMIT 10;
```

The `SELECT` returns the three rows:

```text
| id | name |
+----+------+
|  1 |    a |
|  2 |    b |
|  3 |    c |
+----+------+
```

Fluss keeps its data inside its containers, so [`odctl down` removes it](https://jaehyeon.me/odctl/latest/how-it-works/#where-data-lives).

The Flink UI lists the two jobs:

## From Another Container

Inside the [`odctl` network](https://jaehyeon.me/odctl/latest/how-it-works/#how-you-reach-a-service), set a Fluss client's bootstrap servers to `fluss-coordinator:9123`.

## Runnable Example

Save this file as `example.sh` and run it with `bash example.sh` in the folder that holds your `.odctl` workspace. It waits until the tablet server has registered, then runs the SQL above with a table of its own for each run:

```bash
#!/usr/bin/env bash
# Starts fluss and flink-lite, then writes three rows to a Fluss table with
# Flink SQL and reads them back. Each run uses its own table name.
set -euo pipefail

odctl up fluss flink-lite

# The tablet server registers in ZooKeeper a few seconds after it starts.
until docker exec fluss-zookeeper zkCli.sh -server localhost:2181 ls /fluss/tabletservers/ids 2>/dev/null | grep '^\[0' >/dev/null; do
  sleep 2
done

run=$(date +%s)
docker exec -i flink-jobmanager /opt/flink/bin/sql-client.sh <<SQL | grep -E '^[|+]|ERROR'
SET 'execution.runtime-mode' = 'batch';
SET 'table.dml-sync' = 'true';
SET 'sql-client.execution.result-mode' = 'tableau';
CREATE CATALOG fluss_catalog WITH ('type' = 'fluss', 'bootstrap.servers' = 'fluss-coordinator:9123');
CREATE DATABASE IF NOT EXISTS fluss_catalog.demo;
CREATE TABLE fluss_catalog.demo.t_$run (id BIGINT, name STRING, PRIMARY KEY (id) NOT ENFORCED);
INSERT INTO fluss_catalog.demo.t_$run VALUES (1, 'a'), (2, 'b'), (3, 'c');
SELECT * FROM fluss_catalog.demo.t_$run LIMIT 10;
SQL
```

It prints the same three rows as the `SELECT` above.
