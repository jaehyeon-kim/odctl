# Metadata and Lineage

## OpenMetadata

Profiles: `metadata`. Stack `metadata`, defined in `compose-metadata.yml`.

### metadata

Depends on: `postgres`. `odctl up metadata` also starts: `deps`, `postgres`.

```text
• OpenMetadata UI & REST API:
  - External (host): http://127.0.0.1:8585
  - Internal (Docker): http://openmetadata-server:8585
• Ingestion Pipeline UI:
  - External (host): http://127.0.0.1:8087
  - Internal (Docker): http://openmetadata-ingestion:8080
• Default Admin: admin@open-data.local / admin
```

| Service                  | Image                                                 | Host:container ports     | Memory limit |
| ------------------------ | ----------------------------------------------------- | ------------------------ | ------------ |
| `openmetadata-es`        | `docker.elastic.co/elasticsearch/elasticsearch:9.3.0` | `9200:9200`, `9300:9300` | `2g`         |
| `openmetadata-migrate`   | `docker.getcollate.io/openmetadata/server:2.0.1`      | none                     | `1g`         |
| `openmetadata-server`    | `docker.getcollate.io/openmetadata/server:2.0.1`      | `8585:8585`, `8586:8586` | `2g`         |
| `openmetadata-ingestion` | `docker.getcollate.io/openmetadata/ingestion:2.0.1`   | `8087:8080`              | `1500m`      |

## Marquez

Profiles: `lineage`. Stack `obsv`, defined in `compose-obsv.yml`.

### lineage

Depends on: `postgres`. `odctl up lineage` also starts: `deps`, `postgres`.

```text
• Marquez API Metadata Endpoint:
  * External (host): http://127.0.0.1:5002
  * Internal (Docker): http://marquez-api:5000
• Marquez Lineage Graph Web UI:
  * External (host): http://127.0.0.1:3003
  * Internal (Docker): http://marquez-web:3000
```

| Service       | Image                               | Host:container ports     | Memory limit |
| ------------- | ----------------------------------- | ------------------------ | ------------ |
| `marquez-api` | `marquezproject/marquez:0.51.1`     | `5002:5000`, `5001:5001` | `1g`         |
| `marquez-web` | `marquezproject/marquez-web:0.51.1` | `3003:3000`              | `512m`       |
