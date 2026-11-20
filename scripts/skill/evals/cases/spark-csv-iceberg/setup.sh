#!/usr/bin/env bash
# Copies the prepared Python of this suite into the run's workspace, then points its
# scripts at the copy. `make_suite.py` writes the prepared copy's path into python-path,
# beside the case folders; claude plugin eval runs this script by its full path, from
# the workspace, before the sandbox starts.
set -eu
prepared=$(cat "$(dirname "$0")/../python-path")
cp -R "$prepared" py
# Why: the path is matched and replaced as literal text, so a character such as [ in it
# cannot act as a pattern; perl reads both paths from the environment, so the single
# quotes are meant
# shellcheck disable=SC2016
grep -lF "$prepared/" py/bin/* | PREP="$prepared/" NEW="$PWD/py/" xargs perl -pi -e 's/\Q$ENV{PREP}\E/$ENV{NEW}/g'
# The request describes a workspace the user already made with `odctl init`.
py/bin/odctl init --yes >/dev/null
# The request names a file the user already has in the current folder.
cat > trips.csv <<'CSV'
trip_id,pickup_ts,fare
1,2026-11-01 08:15:00,12.50
2,2026-11-01 08:40:00,8.00
3,2026-11-01 09:05:00,23.75
4,2026-11-02 17:30:00,15.20
5,2026-11-02 18:10:00,9.90
6,2026-11-03 07:55:00,31.00
CSV
