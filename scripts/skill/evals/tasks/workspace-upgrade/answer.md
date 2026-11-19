# workspace-upgrade

Answer sheet of the case `workspace-upgrade`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A8 (workspace file assumed), A4 (odctl CLI behaviour assumed), A7 (what a command keeps or removes).

## Records

- planning `odctl/release/1.8.0/audit.md:11` (M3): an edit did nothing on an older `.env`, because `init` copies only missing top-level entries.
- github `jaehyeon-kim/odctl#127`: projects ran a cached `latest` image because they did not run `odctl init`; the image tag a workspace runs is the one its `.env` sets.

## Right answer

- The warning comes from `.odctl/.env`'s `TAG` differing from the CLI's version, and it names the fix: `odctl init --force`, which resets local edits (`src/odctl/main.py:164-172`; `src/odctl/workspace.py:47-66`).
- A plain `odctl init` changes nothing here: it copies only the top-level files and folders that are missing and writes `.env` only when it is missing or with `--force` (`src/odctl/workspace.py:197-213`; `docs/how-it-works.md:143`). The old compose files, `registry.yml` and `TAG` stay.
- `odctl init --force` deletes `.odctl` and copies the bundled files again with `TAG` set to the CLI version (`workspace.py:183-226`; `docs/how-it-works.md:267`). It asks first unless `--yes` is given (`main.py:326-330`), so a script passes `--force --yes` (`docs/how-it-works.md:270`).
- The Trino edit is lost by that, so it is applied again after it, to the new file: `sed -i.bak 's/"127.0.0.1:8080:8080" # Trino/"127.0.0.1:8180:8080" # Trino/' .odctl/compose-analytics.yml` (`docs/how-it-works.md:184-185`), and checked by reading the line back or with `odctl explain trino`. Keeping a backup of the old workspace before `--force` is good practice and not required.
- Any other edit in the old workspace is lost the same way, so the reply tells the user to compare the old files with the new ones, or the run compares them itself, for example with `diff -r` against a backup. The setup made only the `TAG` and Trino changes.
- Nothing is running, so no `recreate` is needed; the next `odctl up` uses the new files and images. A `odctl recreate trino` stated as needed only because the workspace changed is not counted.

## Wrong answers seen or expected

- A8: `odctl init` with no `--force`, stated to update the workspace.
- A8: only `TAG` edited in `.odctl/.env` to the new version, with no check of the workspace's compose files and `registry.yml` against the installed version: the warning goes, but those files can stay the old version's (the warning says so, `main.py:168-170`). A run that compares `.odctl/` with the installed resources, finds only `TAG` and the Trino port differ, and then edits `TAG` alone is right for this workspace, because its setup made it with the current odctl.
- A8: the old `compose-analytics.yml` copied back over the new one after `--force`, which brings back the old version's file in place of applying the one edit.
- A4: `odctl init --force` in a script with no `--yes`, or an option such as `odctl upgrade` or `odctl init --update`, which do not exist.
- A7: a statement that `odctl init --force` keeps the edits, or the Trino port not applied again after it.
