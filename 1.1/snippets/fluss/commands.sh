# Commands from docs/guides/fluss.md. .github/scripts/smoke.sh runs the ZooKeeper
# section, and pipes steps.sql into the SQL client instead of a terminal.

# --8<-- [start:registrations]
docker exec fluss-zookeeper zkCli.sh -server localhost:2181 ls /fluss/tabletservers/ids
docker exec fluss-zookeeper zkCli.sh -server localhost:2181 get /fluss/coordinators/active
# --8<-- [end:registrations]

# --8<-- [start:sql-client]
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
# --8<-- [end:sql-client]
