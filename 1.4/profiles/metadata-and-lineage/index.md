# Metadata and Lineage

## OpenMetadata

Profiles: `metadata`. Stack `metadata`, defined in `compose-metadata.yml`.

### metadata

Depends on: `postgres`, `storage`. `odctl up metadata` also starts: `deps`, `postgres`, `storage`.

```text
• OpenMetadata UI & REST API (Credentials: admin@odctl.io / admin, or
  user@odctl.io / password, on a new database; a database from an
  earlier release keeps admin@open-data.local and user@open-data.local,
  both with the password admin):
  - External (host): http://127.0.0.1:8585
  - Internal (Docker): http://openmetadata-server:8585
• Ingestion Pipeline UI (Credentials: user / password):
  - External (host): http://127.0.0.1:8087
  - Internal (Docker): http://openmetadata-ingestion:8080
• Custom connectors: files in s3://openmetadata/connectors, checked every
  15 seconds and copied into the ingestion container when they change.
• AutoPilot (default agents for a service added in the UI) is off unless
  METADATA_AUTOPILOT="true" is set in .odctl/.env.
```

| Service                  | Image                                                 | Host:container ports     | Memory limit |
| ------------------------ | ----------------------------------------------------- | ------------------------ | ------------ |
| `openmetadata-es`        | `docker.elastic.co/elasticsearch/elasticsearch:9.3.0` | `9200:9200`, `9300:9300` | `2g`         |
| `openmetadata-migrate`   | `docker.getcollate.io/openmetadata/server:2.0.7`      | none                     | `1g`         |
| `openmetadata-server`    | `docker.getcollate.io/openmetadata/server:2.0.7`      | `8585:8585`, `8586:8586` | `2g`         |
| `openmetadata-ingestion` | `docker.getcollate.io/openmetadata/ingestion:2.0.7`   | `8087:8080`              | `1500m`      |
| `openmetadata-init`      | `docker.getcollate.io/openmetadata/ingestion:2.0.7`   | none                     | `64m`        |

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
