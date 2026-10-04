# Customise the workspace

`odctl init` copies everything odctl runs into `.odctl` in the current directory. odctl reads from there whenever the directory exists, so an edit there changes what starts.

| File | What to change |
| --- | --- |
| `compose-*.yml` | Host ports, memory limits and environment variables of each service |
| `registry.yml` | The profiles, their compose files and their dependencies |
| `.env` | `TAG`, extra Python packages for Airflow (`_AIRFLOW_PIP_DEPS`) and the MLflow services (`_MLOPS_PIP_DEPS`), and the model the MLflow model server serves (`MODEL_URI`) |
| `grafana/dashboards/` | The Grafana dashboard for each service |
| `trino/rules.json` | Trino's file-based access control |
| `evidently/config.yaml` | The Evidently server's settings |

## Apply a change

A restart keeps the container, so it does not apply an edited compose file or `.env`. Run `odctl recreate <profile>` to replace the profile's containers from their current definition, and add `--pull` to fetch images again. Recreating discards the data in those containers. `odctl restart <profile>` is enough for files a service reads when it starts, such as `trino/rules.json` and the Grafana dashboards.

## Trino access rules

The shipped `trino/rules.json` grants every identity full table privileges and denies `analyst` schema ownership. It names no catalog, schema or table, because those belong to your project. Add your own table rules there for row filtering and column masking, then restart Trino.

## Start again

`odctl init --force` deletes `.odctl` and copies the bundled files again, with `TAG` set to the current CLI version. It asks for confirmation first, because your edits are lost.
