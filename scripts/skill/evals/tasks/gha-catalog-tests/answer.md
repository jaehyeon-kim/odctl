# gha-catalog-tests

Answer sheet of the case `gha-catalog-tests`, written from odctl's sources at commit `b8f3eed` before any run. The reviewer reads it beside the run; the agent never sees it, because it is not in the case folder that `make_suite.py` copies into the skill. Paths are in odctl at commit `b8f3eed`; a path that starts with `planning/` is in the owner's planning repository.

Kinds: A4 (odctl CLI behaviour assumed), A7 (what a command keeps or removes), A11 (host environment assumed), A2 (service called before it is ready), A12 (a number with no reason), A3 (address from the wrong side).

## Records

- planning `odctl/release/1.8.0/audit.md:13` (M5): `uv venv` with no `--python` took the host's newest Python, and the tool crashed.
- planning `odctl/release/1.7.0/audit.md:9` (M3): commands needed `uv` and the page did not say so.
- planning `odctl/release/1.4.0/audit.md:12` (M2): a wait with no limit.
- A12 has no odctl record; this case extends the kind's evidence from desflow (planning `odctl/plan-agent-skill.md`, Kinds, A12).

## Right answer

- Install a pinned odctl, such as `uv tool install odctl==<version>` or `pipx install odctl==<version>`. Without a workspace, odctl runs its own images at the CLI's version (`src/odctl/workspace.py:26-44`; `docs/how-it-works.md:100`, 123), so an unpinned install changes the stack whenever a release comes out. odctl's own workflow installs uv with `astral-sh/setup-uv` and Python with `uv python install` (`.github/workflows/e2e-test.yml:67-76`).
- Set up the host Python for the tests with a stated version (`actions/setup-python` with `python-version`, or `uv python install <version>` and `uv venv --python <version>`), then install `requirements-test.txt`. Each host tool the steps use is installed by the workflow or named in the reply.
- Start with `odctl up catalog`; it also starts `deps`, `postgres` and `storage` (`odctl up catalog --dry-run`; `src/odctl/resources/registry.yml:58`). `odctl up` has no `--yes` and asks nothing (`src/odctl/main.py:405-419`).
- `up` returns when each service runs, and is healthy where it has a health check (`docs/how-it-works.md:34`). The `catalog` service has none (`src/odctl/resources/compose-infra.yml:122-176`), so the job waits for `http://127.0.0.1:8181/v1/config` with a limit before the tests, as odctl's smoke test does (`.github/scripts/smoke.sh:303`, `retry 30 5`). Each count, delay and `timeout-minutes` the agent picks carries its reason.
- The tests run on the runner, so they use `http://127.0.0.1:8181` (the skill's catalog notes); the catalog's warehouse is in SeaweedFS, which the tests reach at `http://127.0.0.1:8333` with `user`/`password` if they read data files.
- Teardown in a step with `if: always()`, so it runs when the tests fail. It removes what the job started: `odctl down catalog storage postgres --volumes --yes`, or `odctl down --all --volumes --yes` on a runner that starts with no containers, as odctl's own workflow does (`.github/workflows/e2e-test.yml:124`, 129). A named `down --volumes` that covers every profile with a container asks "This will destroy ALL profiles and WIPE ALL DATA" (`main.py:843-853`, `removes_everything` at 587-634); without `--yes` a step with no input fails with `Abort`, because click raises `Abort` when the answer cannot be read (click 8.5.0, `termui.py:331-332`). That a GitHub Actions step gives the command no input is inferred, not run. In a CI job on its own runner, either teardown with `--volumes --yes` and no `--dry-run` is not A7: the runner holds only what the job started, and the job ends with it.

## Wrong answers seen or expected

- A4: `odctl up catalog --yes` or another option `up` does not take; `odctl ps` with no profile and no `--all`.
- A4: a named teardown with `--volumes` that covers every running profile, or `down --all --volumes`, without `--yes` (both ask, `main.py:844-853`), or a statement that it asks nothing.
- A7: a teardown of `catalog` alone stated to remove everything the job started; `down catalog` leaves `postgres` and `storage` running (`docs/how-it-works.md:49`).
- A7: the teardown not under `if: always()`, so a failed test leaves the stack up, against the request.
- A11: no Python version set for the tests, or `uv`, `pipx` or `jq` used without a step that installs it.
- A11: odctl installed with no version.
- A2: tests started straight after `odctl up catalog` with no wait on the catalog, or a wait with no limit, or a fixed `sleep`.
- A3: `http://catalog:8181` used by the tests on the runner.
- A12: a retry count, delay or `timeout-minutes` with no reason.
