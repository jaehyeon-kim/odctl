# Commands from docs/guides/fluss.md. .github/scripts/smoke.sh runs the ZooKeeper
# section, and pipes steps.sql into the SQL client instead of a terminal.

# smoke.sh does not run the up sections, because the e2e workflow starts
# each profile itself; they are the commands as the page shows them.
# --8<-- [start:up]
odctl up fluss flink-lite
# --8<-- [end:up]

# --8<-- [start:registrations]
docker exec fluss-zookeeper zkCli.sh -server localhost:2181 ls /fluss/tabletservers/ids
docker exec fluss-zookeeper zkCli.sh -server localhost:2181 get /fluss/coordinators/active
# --8<-- [end:registrations]

# --8<-- [start:sql-client]
docker exec -it flink-jobmanager /opt/flink/bin/sql-client.sh
# --8<-- [end:sql-client]
