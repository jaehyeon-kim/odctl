# Messaging

## Kafka

Profiles: `kafka-lite`, `kafka-full`. Stack `kafka`, defined in `compose-kafka.yml`.

### kafka-lite

Depends on: `deps`. `odctl up kafka-lite` also starts: `deps`.

```text
• Kafka UI:
  - External (host): http://127.0.0.1:8086
  - Internal (Docker): http://kafka-ui:8080
• Schema Registry & Connect:
  - External (host): http://127.0.0.1:8081 / http://127.0.0.1:8083
• Bootstrap Servers (1-Node Lite):
  - External (host): 127.0.0.1:9092
  - Internal (Docker): broker-1:19092
```

| Service    | Image                               | Host:container ports | Memory limit |
| ---------- | ----------------------------------- | -------------------- | ------------ |
| `kafka`    | `apache/kafka:4.4.0`                | `9092:9092`          | `1500m`      |
| `connect`  | `apache/kafka:4.4.0`                | `8083:8083`          | `2g`         |
| `karapace` | `ghcr.io/aiven-open/karapace:6.2.4` | `8081:8081`          | `512m`       |
| `kafka-ui` | `ghcr.io/kafbat/kafka-ui:v1.5.0`    | `8086:8080`          | `512m`       |

### kafka-full

Depends on: `deps`. `odctl up kafka-full` also starts: `deps`.

```text
• Kafka UI:
  - External (host): http://127.0.0.1:8086
  - Internal (Docker): http://kafka-ui:8080
• Schema Registry & Connect:
  - External (host): http://127.0.0.1:8081 / http://127.0.0.1:8083
• Bootstrap Servers (3-Node Cluster):
  - External (host): 127.0.0.1:9092, 127.0.0.1:9093, 127.0.0.1:9094
  - Internal (Docker): broker-1:19092, broker-2:19093, broker-3:19094
```

| Service    | Image                               | Host:container ports | Memory limit |
| ---------- | ----------------------------------- | -------------------- | ------------ |
| `kafka-1`  | `apache/kafka:4.4.0`                | `9092:9092`          | `1500m`      |
| `kafka-2`  | `apache/kafka:4.4.0`                | `9093:9093`          | `1500m`      |
| `kafka-3`  | `apache/kafka:4.4.0`                | `9094:9094`          | `1500m`      |
| `connect`  | `apache/kafka:4.4.0`                | `8083:8083`          | `2g`         |
| `karapace` | `ghcr.io/aiven-open/karapace:6.2.4` | `8081:8081`          | `512m`       |
| `kafka-ui` | `ghcr.io/kafbat/kafka-ui:v1.5.0`    | `8086:8080`          | `512m`       |
