# Commands from docs/guides/temporal-workers.md. .github/scripts/smoke.sh installs
# the same SDK version into its own environment instead of with pip.

# --8<-- [start:install]
odctl up temporal
pip install temporalio==1.34.0
# --8<-- [end:install]
