# Commands from docs/guides/valkey.md. .github/scripts/smoke.sh runs each section.

# --8<-- [start:round-trip]
vk=redis://user:password@localhost:6379
docker exec valkey valkey-cli --no-auth-warning -u "$vk" ping
docker exec valkey valkey-cli --no-auth-warning -u "$vk" mset 'model:1' '{"a":1}' 'model:2' '{"a":2}'
docker exec valkey valkey-cli --no-auth-warning -u "$vk" mget 'model:1' 'model:2'
docker exec valkey valkey-cli --no-auth-warning -u "$vk" del 'model:1' 'model:2'
# --8<-- [end:round-trip]
