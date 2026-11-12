# Stream and Batch Processing

## Apache Flink

Profiles: `flink-lite`, `flink-full`. Stack `flink`, defined in `compose-flink.yml`.

### flink-lite

Depends on: `catalog`. `odctl up flink-lite` also starts: `catalog`, `deps`, `postgres`, `storage`.

```text
• Flink JobManager UI (1 TaskManager):
  - External (host): http://127.0.0.1:8082
  - Internal (Docker): http://jobmanager:8081
• SQL Gateway REST:
  - External (host): http://127.0.0.1:8084
  - Internal (Docker): http://flink-sql-gateway:8083
```

| Service         | Image              | Host:container ports | Memory limit |
| --------------- | ------------------ | -------------------- | ------------ |
| `jobmanager`    | `flink:2.2-java17` | `8082:8081`          | `1500m`      |
| `taskmanager-a` | `flink:2.2-java17` | none                 | `3500m`      |
| `sql-gateway`   | `flink:2.2-java17` | `8084:8083`          | `1g`         |

### flink-full

Depends on: `catalog`. `odctl up flink-full` also starts: `catalog`, `deps`, `postgres`, `storage`.

```text
• Flink JobManager UI (3 TaskManagers):
  - External (host): http://127.0.0.1:8082
  - Internal (Docker): http://jobmanager:8081
• SQL Gateway REST:
  - External (host): http://127.0.0.1:8084
  - Internal (Docker): http://flink-sql-gateway:8083
```

| Service         | Image              | Host:container ports | Memory limit |
| --------------- | ------------------ | -------------------- | ------------ |
| `jobmanager`    | `flink:2.2-java17` | `8082:8081`          | `1500m`      |
| `taskmanager-a` | `flink:2.2-java17` | none                 | `3500m`      |
| `taskmanager-b` | `flink:2.2-java17` | none                 | `3500m`      |
| `taskmanager-c` | `flink:2.2-java17` | none                 | `3500m`      |
| `sql-gateway`   | `flink:2.2-java17` | `8084:8083`          | `1g`         |

## Apache Spark

Profiles: `spark-lite`, `spark-full`. Stack `spark`, defined in `compose-spark.yml`.

### spark-lite

Depends on: `catalog`. `odctl up spark-lite` also starts: `catalog`, `deps`, `postgres`, `storage`.

```text
• Spark Master UI (1 Worker):
  - External (host): http://127.0.0.1:9080
  - Internal (Docker): http://spark-master:8080
• Master RPC:
  - External (host): spark://127.0.0.1:7077
  - Internal (Docker): spark://spark-master:7077
• Spark History Server:
  - External (host): http://127.0.0.1:18080
  - Internal (Docker): http://spark-history:18080
```

| Service          | Image                                            | Host:container ports     | Memory limit |
| ---------------- | ------------------------------------------------ | ------------------------ | ------------ |
| `spark-master`   | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9080:8080`, `7077:7077` | `1g`         |
| `spark-worker-1` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9081:8081`              | `2g`         |
| `spark-history`  | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `18080:18080`            | `1g`         |

### spark-full

Depends on: `catalog`. `odctl up spark-full` also starts: `catalog`, `deps`, `postgres`, `storage`.

```text
• Spark Master UI (3 Workers):
  - External (host): http://127.0.0.1:9080
  - Internal (Docker): http://spark-master:8080
• Master RPC:
  - External (host): spark://127.0.0.1:7077
  - Internal (Docker): spark://spark-master:7077
• Spark History Server:
  - External (host): http://127.0.0.1:18080
  - Internal (Docker): http://spark-history:18080
```

| Service          | Image                                            | Host:container ports     | Memory limit |
| ---------------- | ------------------------------------------------ | ------------------------ | ------------ |
| `spark-master`   | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9080:8080`, `7077:7077` | `1g`         |
| `spark-worker-1` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9081:8081`              | `2g`         |
| `spark-worker-2` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9082:8081`              | `2g`         |
| `spark-worker-3` | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `9083:8081`              | `2g`         |
| `spark-history`  | `ghcr.io/jaehyeon-kim/odctl/spark:<CLI version>` | `18080:18080`            | `1g`         |
