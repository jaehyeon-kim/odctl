# Commands from docs/guides/feast-vector-retrieval.md. .github/scripts/smoke.sh
# installs the same client into its own environment, then runs the other sections
# from a folder holding a copy of vector_repo/.

# smoke.sh does not run the up sections, because the e2e workflow starts
# each profile itself; they are the commands as the page shows them.
# --8<-- [start:install]
odctl up postgres
pip install "feast[duckdb,postgres]==0.66.0"
# --8<-- [end:install]

# --8<-- [start:apply]
feast -c vector_repo apply --skip-source-validation
# --8<-- [end:apply]
