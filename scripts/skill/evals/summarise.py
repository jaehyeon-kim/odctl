"""Makes the result table of an evaluation from the JSON lines of all its runs.

Usage:

    python summarise.py --plan PLAN.tsv --grades GRADES.jsonl [...] --reviews REVIEWS.jsonl [...]

`--plan` lists the runs the evaluation made, one per line: the task (a folder name under
`cases/`, such as `spark-kafka`), the version, the model and the run number, separated by
tabs. `--grades` takes files of `facts.py` lines, and `--reviews` files of the blind
reviewer's lines (`review_rubric.md`), to which the main session has added `version`, `model`
and `run`. Both have the fields `task`, `kind`, `count`, `version`, `model`, `run`.

A run with a line missing would read as a run with no mistake, and a run graded twice may hold
the lines of two gradings, so the runs to expect come from the plan, not from the lines. Each
run of the plan has exactly one `FACTS` line of `facts.py` and exactly one `REVIEWED` line of
the reviewer, which may write any number of lines of the kinds it judges. The script lists
each run that lacks a line, holds one twice, is in the plan twice or is not in the plan, and each reviewer line of a
kind it does not judge, and exits 1.

A kind counts at most once per run: a `count` above 0 on any line of that run and kind scores
1. The output is a markdown table per model and version: for each kind, the mean number of
runs with that mistake per task, with the spread (the largest minus the smallest of the
per-run-number means) when a task has several runs; then the total over kinds, whose spread is
that of the per-run-number totals.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

# The kinds the reviewer judges (review_rubric.md): odctl's lifecycle and dependencies
KINDS = ["A1", "A2", "A3", "A4", "A7", "A9"]
# Why: reviews written before the rubric was narrowed hold these, which are not counted
DROPPED = ["A6", "A8", "A10", "A11", "A12"]
FACTS = "FACTS"
REVIEWED = "REVIEWED"

# (task, version, model, run)
RunKey = Tuple[str, str, str, str]


class Stat(NamedTuple):
    """A mean over run numbers of the per-task mean, and the spread of those means."""

    mean: float
    spread: float


def load(paths: List[Path]) -> List[dict]:
    """Returns every JSON object line of the given files."""
    rows = []
    for path in paths:
        for line in path.read_text("utf-8").splitlines():
            line = line.strip()
            if line.startswith("{"):
                rows.append(json.loads(line))
    return rows


def load_plan(path: Path) -> List[RunKey]:
    """Returns the runs of a plan file, one tab-separated (task, version, model, run) a line."""
    runs = []
    for line in path.read_text("utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            task, version, model, run = line.split("\t")
            runs.append((task, version, model, run))
    return runs


def run_key(row: dict) -> RunKey:
    """Returns the (task, version, model, run) of a line."""
    return (
        row["task"],
        str(row.get("version", "")),
        str(row.get("model", "")),
        str(row.get("run", "")),
    )


def problems(plan: List[RunKey], grades: List[dict], reviews: List[dict]) -> List[str]:
    """Returns one sentence per run whose lines are missing, repeated or not in the plan."""
    facts: Dict[RunKey, int] = defaultdict(int)
    reviewed: Dict[RunKey, int] = defaultdict(int)
    found = []
    for row in grades:
        if row["kind"] == FACTS:
            facts[run_key(row)] += 1
        else:
            found.append(f"{run_key(row)}: facts.py line of kind {row['kind']}")
    for row in reviews:
        if row["kind"] == REVIEWED:
            reviewed[run_key(row)] += 1
        elif row["kind"] not in KINDS + DROPPED:
            found.append(
                f"{run_key(row)}: reviewer line of kind {row['kind']}, which it does not judge"
            )
    planned = set(plan)
    for key in sorted(planned):
        if plan.count(key) > 1:
            found.append(f"{key}: {plan.count(key)} times in the plan, want 1")
    for key in plan:
        if facts[key] != 1:
            found.append(f"{key}: {facts[key]} FACTS lines, want 1")
        if reviewed[key] != 1:
            found.append(f"{key}: {reviewed[key]} REVIEWED lines, want 1")
    for key in sorted(set(facts) | set(reviewed) | {run_key(r) for r in reviews}):
        if key not in planned:
            found.append(f"{key}: not in the plan")
    return found


def scores(plan: List[RunKey], reviews: List[dict]) -> Dict[RunKey, Dict[str, int]]:
    """Returns, for each run of the plan, 1 for each kind with a mistake and 0 for the others."""
    per_run = {key: {kind: 0 for kind in KINDS} for key in plan}
    for row in reviews:
        key = run_key(row)
        if key in per_run and row["kind"] in KINDS and int(row["count"]) > 0:
            per_run[key][row["kind"]] = 1
    return per_run


def stat(values: List[float]) -> Stat:
    """Returns the mean of the values and their spread (largest minus smallest)."""
    return Stat(sum(values) / len(values), max(values) - min(values))


def tables(plan: List[RunKey], per_run: Dict[RunKey, Dict[str, int]]) -> List[str]:
    """Returns the markdown table of each (model, version), as the module docstring sets out."""
    groups: Dict[Tuple[str, str], Dict[str, List[RunKey]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for key in plan:
        task, version, model, run = key
        groups[(model, version)][run].append(key)
    lines = []
    for (model, version), by_number in sorted(groups.items()):
        lines += [
            f"## {model}, version {version}",
            "",
            "| Kind | Mean per task | Spread |",
            "|---|---|---|",
        ]
        totals = []
        for keys in by_number.values():
            totals.append(sum(sum(per_run[k].values()) for k in keys) / len(keys))
        for kind in KINDS:
            means = [
                sum(per_run[k][kind] for k in keys) / len(keys)
                for keys in by_number.values()
            ]
            s = stat(means)
            lines.append(f"| {kind} | {s.mean:.2f} | {s.spread:.2f} |")
        s = stat(totals)
        lines += [f"| Total | {s.mean:.2f} | {s.spread:.2f} |", ""]
    return lines


def main(argv: Optional[List[str]] = None) -> int:
    """Prints the tables, or the runs whose lines are wrong.

    Args:
        argv: The command line without the program name; None reads `sys.argv`.

    Returns:
        0, or 1 when a run's lines are missing, repeated or not in the plan.
    """
    parser = argparse.ArgumentParser(description="Makes the evaluation's result table.")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--grades", type=Path, nargs="+", required=True)
    parser.add_argument("--reviews", type=Path, nargs="+", required=True)
    args = parser.parse_args(argv)
    plan = load_plan(args.plan)
    grades = load(args.grades)
    reviews = load(args.reviews)
    found = problems(plan, grades, reviews)
    if found:
        print("\n".join(found))
        return 1
    print("\n".join(tables(plan, scores(plan, reviews))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
