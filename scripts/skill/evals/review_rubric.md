# Rubric of the blind reviewer

An Opus reviewer reads the folder of one run and lists each mistake of the kinds below with its file and line. The kinds are those of the plan's Kinds table that a run with no containers can show: every kind except A5, output that only an image shows. `facts.py` measures nothing; it writes the facts below, and the reviewer judges every kind from them, the run's files and its full transcript. The reviewer is not told which version of the skill, which model or which run number made the run. It reads, runs nothing, and changes no file.

## What the reviewer gets

One folder, which `facts.py` writes from the run that `claude plugin eval --keep-temp` kept (`run_task.md`, Steps, step 5). In every file of it, the path of the skill copy reads `<skill>`, the suite folder `<suite>`, the run's kept folder `<run>` and the odctl version under test `<version>`, so that no text tells the version.

- `files/`: each file the prompt asks for, as the agent left it. A `.py` or `.sh` file has `.txt` added and is otherwise unchanged.
- `trace.jsonl`: the run's full transcript, one JSON object per line as `claude -p --output-format stream-json` writes it. A line of `"type": "assistant"` holds the agent's text and its tool calls (`"type": "tool_use"`, with `name`, `input` and `id`); a line of `"type": "user"` holds the result of each call (`"type": "tool_result"`, with the call's id as `tool_use_id`), that is, what the command printed or the file the agent read. The reviewer reads it in full. Docker was not available in the run, so a command that needs it failed there; that failure is not a mistake.
- `task/prompt.md`: the request as the agent got it, after a settings block.
- `task/answer.md`: the case's answer sheet, written from odctl's sources before any run: the records the case comes from, its kinds, the right answer with its sources, and wrong answers seen or expected. It guides the judgement; a run that meets the request another way that works is not a mistake.
- `facts.json`: `missing`, the files the prompt asks for that the run did not write; and under `odctl`, what odctl itself says about the profiles the right answer starts: `list` (`odctl list --json`), `explain` (`odctl explain <profile> --json`, with each service's container name, host ports, usage text and role), `dry_run` (the start order of `odctl up <profiles> --dry-run`), and `compose`, each service of their compose files with its container name, network aliases, ports (host side first), `expose` and whether it has a health check.
- `skill/`: the `SKILL.md` and `references/` pages of the skill copy the run had, so that a claim about odctl can be checked against what the agent could read. A run without the skill has no `skill/` folder.

## Output

One JSON line per mistake, and nothing else:

```json
{"task": "spark-kafka", "kind": "A3", "count": 1, "file": "read_orders.py", "line": 7, "evidence": "uses localhost:9092 inside spark-master; from a container the broker is broker-1:19092 (facts.json, compose, kafka aliases)"}
```

`count` is always 1, and `file` names the agent's file without the `.txt`, or `trace.jsonl` for a mistake that is only in a command the agent ran. A run with no mistake of a kind has no line for it. After the last mistake, the reviewer writes one line that says it read the run, whatever it found:

```json
{"task": "spark-kafka", "kind": "REVIEWED", "count": 0}
```

`summarise.py` exits with an error for a run that has no `REVIEWED` line or two of them, so a run the reviewer skipped is not read as a run with no mistake, and a run read twice is not counted twice. The main session sets `task`, `version`, `model` and `run` from its own list before it gives the lines to `summarise.py`. A mistake is counted once per place: the same wrong address in a script and in `reply.md` is two places. `summarise.py` counts each kind once per run.

What counts is what the user would run or rely on: the files the prompt asks for, and the statements in `reply.md`. A command the agent tried in the transcript and then corrected is not a mistake. A statement or command in a file is judged against `facts.json`, `answer.md`, the pages of `skill/` and the tool results in `trace.jsonl`.

## A1: a step needs an earlier step

A file runs a step before a step it needs, or leaves out a profile or a step that the next one needs.

- Wrong: `odctl up trino` alone before a query on the Iceberg catalog. `facts.json` `explain.trino.starts` lists no `catalog` or `storage`, and the Iceberg catalog fails at query time without them.
- Wrong: the push to Feast before the push source is applied in the server.
- Right: `odctl up catalog trino`, or the agent ran `odctl up trino --dry-run` and added what it did not start.

## A2: a service called before it is ready

A call to a service right after `odctl up`, `restart` or `recreate`, or after a step that the service finishes later, with no wait on a check of what the task needs, or a wait with no limit.

- Wrong: `odctl up kafka-lite` and then a consumer, with no wait. `facts.json` `compose` shows `kafka` has no health check, so `up` returns when it runs, not when it answers.
- Wrong: `until <check>; do sleep 2; done` with no count or deadline, or a fixed `sleep 30` in place of a check.
- Wrong: a healthy Langfuse container, or a 200 on the send, taken to mean the trace is stored.
- Not a mistake: no extra wait for a service whose `healthcheck` is true in `facts.json`, because `up` already waits for it. An extra wait there is A4.

## A3: an address or a name from the wrong side, or guessed

An address used from the side that cannot reach it, or a host name, port or login that `facts.json`, the skill or a tool result does not give.

- Wrong: `localhost:9092` in code that runs in a container; `broker-1:19092` or `catalog:8181` in code that runs on the host.
- Wrong: `iceberg-rest:8181`, `storage:8333` (a profile name used as a host name), `admin/admin`.
- Right: from a container, a name from `compose` `container_name` or `aliases` with the container port; from the host, `127.0.0.1` with the host side of `ports`.

## A4: odctl CLI behaviour assumed or invented

A command, option or behaviour of odctl that does not exist or is not as used: a command not in the skill's Commands table or `odctl --help`, an option the command does not take, or a claim about what it does that its help, the skill or a run does not show.

- Wrong: `odctl ps` or `odctl ps --json` with no profile and no `--all`, which exits 1.
- Wrong: `odctl trino`, `odctl exec`, `odctl up spark` (the profiles are `spark-lite` and `spark-full`).
- Wrong: an extra readiness probe for a service `up` already waits for, with a claim that `up` does not wait.

## A6: service behaviour stated without a run or its source

A statement in a file or `reply.md` about how a service behaves (what an API needs, what a setting does, why something failed), or code that depends on it, where no tool result in `trace.jsonl`, no page of `skill/` and no fact in `facts.json` shows it, and `answer.md` shows it is wrong or does not show it.

- Wrong: "ClickHouse's async inserts make the read racy, so the test sleeps 2 seconds", when the run never read the stack's ClickHouse settings.
- Wrong: "Langfuse's read needs a time range".
- Not a mistake: a behaviour the run showed, or one the skill states.

## A7: what a command keeps or removes

A teardown, recreate or reset that removes more than the task started, or keeps less than the request needs, or a statement about what it keeps that is wrong.

- Wrong: `odctl down --all`, or `--all --volumes`, when the task started one profile.
- Wrong: `odctl down postgres` and `up` again when the request says the data must stay, or a claim that PostgreSQL's data is in a named volume that survives it.
- Wrong: `down <profile> --volumes` with no `--dry-run` before it, or a claim that the command will ask first.
- Right: `odctl down kafka-lite --volumes --dry-run`, then `odctl down kafka-lite --volumes`.

## A8: a stack setting, image content or workspace file assumed

Code or a statement that relies on a setting, a file in an image or a workspace file without reading it, where `answer.md`, `facts.json` or the stack shows otherwise.

- Wrong: `odctl recreate postgres` after an edit of `TZ`, stated to change PostgreSQL's zone, when PostgreSQL reads `TZ` only when it creates its data folder.
- Wrong: `--packages org.apache.spark:spark-sql-kafka...` because the Spark image is assumed not to hold the connector.
- Wrong: an edit of the packaged compose file in place of `.odctl/.env` or the workspace copy.

## A9: state from an earlier run breaks the next

A setup or test that fails, or passes on old values, when it runs a second time on the same stack.

- Wrong: `CREATE TABLE t` with no `IF NOT EXISTS` and no drop first; rows appended again on every run.
- Wrong: `feast teardown` as the cleanup, or a DAG left unpaused in the bucket.
- Right: each step is safe to run twice, and what the script registered is removed or reused.

## A10: a check that cannot fail

A check whose test passes whatever the thing it checks is, or that hides a failure.

- Wrong: `grep -q 'retention.ms=86400000'`, which also matches `delete.retention.ms=86400000`.
- Wrong: `|| true` after a step that must succeed, or a pipe without `pipefail` whose first command fails.
- Wrong: a check against a document or a file the script wrote, not the running service.

## A11: host environment assumed

A file that needs a host tool, a Python version or a time zone it does not name or pin.

- Wrong: `uv venv .venv` with no `--python`, for Feast, which needs Python 3.11 or newer.
- Wrong: a script that needs `uv`, `jq` or `curl` on the host and neither checks for it nor says so in `reply.md`.
- Wrong: a time filter written in the host's local time against containers in UTC.

## A12: a number given with no reason

A retry count, a wait limit, a timeout or a delay the agent chose, written with no comment or sentence that says why.

- Wrong: `retry 30 5 ...` with no reason. Right: the same line with a comment that says where the limit comes from, such as the start time the agent measured or one the skill gives.
- Not a mistake: a number the prompt gives, a port, or a number that is clear from the line beside it.
