# Commands from docs/guides/evidently-reports.md. .github/scripts/smoke.sh installs
# the same Evidently version with uv instead of pip.

# --8<-- [start:install]
odctl up evidently
pip install evidently==0.7.23
# --8<-- [end:install]
