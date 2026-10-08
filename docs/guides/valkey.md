# Valkey

The `valkey` profile runs the Valkey Bundle image, `valkey/valkey-bundle:9.1.3-alpine`, as one container named `valkey`. The registry describes it as a cache and data store with JSON, Bloom and vector search capabilities. The commands below come from the end-to-end tests, which run them on every release, with the names changed.

```bash
odctl up valkey
```

| Setting | Value |
| --- | --- |
| Address from the host | `127.0.0.1:6379` |
| Address inside the `odctl` network | `valkey:6379` |
| User | `user`, password `password` |
| Memory limit | 512 MB |

## Users and permissions

The unauthenticated `default` user is turned off, so every client logs in as `user`. That user has every command, every key pattern and every Pub/Sub channel. Channels are a separate permission in Valkey, and the profile grants them explicitly, so `PUBLISH` and `SUBSCRIBE` work as well as key commands.

## Write and read keys

`valkey-cli` is in the container. Log in with a URL that carries the user and password:

```bash
vk=redis://user:password@localhost:6379
docker exec valkey valkey-cli --no-auth-warning -u "$vk" ping
docker exec valkey valkey-cli --no-auth-warning -u "$vk" mset 'model:1' '{"a":1}' 'model:2' '{"a":2}'
docker exec valkey valkey-cli --no-auth-warning -u "$vk" mget 'model:1' 'model:2'
docker exec valkey valkey-cli --no-auth-warning -u "$vk" del 'model:1' 'model:2'
```

`--no-auth-warning` stops `valkey-cli` printing a warning about the password on the command line. `ping` answers `PONG`. `mset` writes both keys in one command, and `mget` reads them back in one round trip, which is how product-recommender stores and loads its models.

![valkey-cli output for ping, mset, mget and del](../images/valkey-cli.png){ .screenshot }

## Persistence

Valkey writes an append-only file and saves a snapshot every 60 seconds when at least one key has changed. Both files are inside the container, so a restart keeps the data and `odctl down` removes it.

## From another container

Inside the `odctl` network, connect to `valkey:6379` with the same user and password, for example `redis://user:password@valkey:6379` for a Redis client. Feast's online store uses this address, as [Feast with Iceberg](feast-iceberg.md) shows.
