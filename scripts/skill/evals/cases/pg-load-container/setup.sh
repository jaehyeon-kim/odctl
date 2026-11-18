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
# The request names the export the user already has.
printf 'order_id,customer,amount\n1,alice,12.50\n2,bob,7.25\n3,carol,30.00\n' > orders.csv
