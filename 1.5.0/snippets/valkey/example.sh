#!/usr/bin/env bash
# Starts valkey, writes two keys and reads them back, stores a JSON document
# and reads one field of it, then deletes the keys.
set -euo pipefail

odctl up valkey

vk=redis://user:password@localhost:6379
docker exec valkey valkey-cli --no-auth-warning -u "$vk" ping
docker exec valkey valkey-cli --no-auth-warning -u "$vk" mset 'model:1' '{"a":1}' 'model:2' '{"a":2}'
docker exec valkey valkey-cli --no-auth-warning -u "$vk" mget 'model:1' 'model:2'

# Store a JSON document with the JSON module and read one field by its path.
docker exec valkey valkey-cli --no-auth-warning -u "$vk" JSON.SET 'doc:1' '$' '{"name":"odctl","stars":5}'
docker exec valkey valkey-cli --no-auth-warning -u "$vk" JSON.GET 'doc:1' '$.stars'

docker exec valkey valkey-cli --no-auth-warning -u "$vk" del 'model:1' 'model:2' 'doc:1'
