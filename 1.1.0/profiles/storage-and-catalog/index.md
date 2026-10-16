# Storage and catalog

## PostgreSQL

Profiles: `postgres`. Stack `postgres`, defined in `compose-infra.yml`.

### postgres

Depends on: `deps`. `odctl up postgres` also starts: `deps`.

```text
• Postgres JDBC:
  - External (host): jdbc:postgresql://127.0.0.1:5432/odctl
  - Internal (Docker): jdbc:postgresql://postgres:5432/odctl
  - Credentials: user / password
• Extensions, created in the `vector` database:
  - vector (pgvector): vector columns and HNSW or IVFFlat indexes
  - pg_textsearch: BM25 keyword ranking, for hybrid search with pgvector
  - postgis: geometry and geography types and spatial queries
  Run CREATE EXTENSION in another database to use them there.
```

| Service    | Image                                               | Host:container ports | Memory limit |
| ---------- | --------------------------------------------------- | -------------------- | ------------ |
| `postgres` | `ghcr.io/jaehyeon-kim/odctl/postgres:<CLI version>` | `5432:5432`          | `1g`         |

## SeaweedFS

Profiles: `storage`. Stack `storage`, defined in `compose-infra.yml`.

### storage

Depends on: `deps`. `odctl up storage` also starts: `deps`.

```text
• S3 Browser UI:
  - External (host): http://127.0.0.1:8889
  - Internal (Docker): http://seaweed:8888
• S3 API Endpoint:
  - External (host): http://127.0.0.1:8333
  - Internal (Docker): http://seaweed:8333
  - Default AWS Keys: user / password
```

| Service        | Image                      | Host:container ports                  | Memory limit |
| -------------- | -------------------------- | ------------------------------------- | ------------ |
| `seaweed`      | `chrislusf/seaweedfs:4.48` | `8333:8333`, `8889:8888`, `9333:9333` | `512m`       |
| `seaweed-init` | `chrislusf/seaweedfs:4.48` | none                                  | not set      |

## Iceberg REST catalog

Profiles: `catalog`. Stack `catalog`, defined in `compose-infra.yml`.

### catalog

Depends on: `postgres`, `storage`. `odctl up catalog` also starts: `deps`, `postgres`, `storage`.

```text
• REST API Endpoint:
  - External (host): http://127.0.0.1:8181
  - Internal (Docker): http://catalog:8181
```

| Service   | Image                               | Host:container ports | Memory limit |
| --------- | ----------------------------------- | -------------------- | ------------ |
| `catalog` | `azul/zulu-openjdk:17-jre-headless` | `8181:8181`          | `512m`       |

## Valkey

Profiles: `valkey`. Stack `store`, defined in `compose-store.yml`.

### valkey

Depends on: `deps`. `odctl up valkey` also starts: `deps`.

```text
• Valkey (Multi-Model Data Store: Cache, JSON, Vector Search):
  * External (host): 127.0.0.1:6379
  * Internal (Docker): valkey:6379
  * Authentication: username 'user', password 'password'
```

| Service  | Image                               | Host:container ports | Memory limit |
| -------- | ----------------------------------- | -------------------- | ------------ |
| `valkey` | `valkey/valkey-bundle:9.1.3-alpine` | `6379:6379`          | `512m`       |

## Apache Fluss

Profiles: `fluss`. Stack `store`, defined in `compose-store.yml`.

### fluss

Depends on: `deps`. `odctl up fluss` also starts: `deps`.

```text
• Fluss Coordinator API:
  * External (host): 127.0.0.1:9123
  * Internal (Docker): fluss-coordinator:9123
• The servers advertise their container names, which resolve only
  inside the odctl network, so run Fluss clients in a container, such
  as Flink.
```

| Service             | Image                | Host:container ports | Memory limit |
| ------------------- | -------------------- | -------------------- | ------------ |
| `fluss-zookeeper`   | `zookeeper:3.9.6`    | none                 | `512m`       |
| `fluss-coordinator` | `apache/fluss:1.0.0` | `9123:9123`          | `1g`         |
| `fluss-tablet-1`    | `apache/fluss:1.0.0` | `9124:9123`          | `2g`         |

## Shared dependencies

Profiles: `deps`. Stack `deps`, defined in `compose-deps.yml`.

### deps

Depends on: nothing. `odctl up deps` also starts: nothing else.

```text
• Runs automatically on 'odctl up'.
• No persistent UI or ports exposed.
```

| Service     | Image                                           | Host:container ports | Memory limit |
| ----------- | ----------------------------------------------- | -------------------- | ------------ |
| `init-deps` | `ghcr.io/jaehyeon-kim/odctl/deps:<CLI version>` | none                 | not set      |
