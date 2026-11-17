"""Shows that the evaluation's scripts work before any counted run (run_task.md, step 1).

Usage:

    <suite>/py/bin/python3.12 selftest.py --python-dir <suite>/py --skill <suite>/odctl

It builds kept runs by hand in a temporary folder, in the layout `claude plugin eval
--keep-temp` leaves (`ROOT/sealed/home/cwd` and `ROOT/out/trace.jsonl`), and checks:

- `facts.py` on a run of every case writes each file the prompt asks for, the transcript, the
  task files and the skill, lists no missing file, and gives the explain, compose and dry-run
  facts of every profile in the case's `task.yaml`; and `check_hidden.py` passes on the result.
- A file the run did not write is listed in `missing`, and `facts.py` works with a relative
  `--python-dir`.
- `facts.py` exits 2 with no line when the transcript, the workspace or the case's
  `task.yaml` cannot be read, because a fact that reads nothing must fail, not count nothing.
- `check_hidden.py` exits 1 when a file names a suite or an odctl version.
- `summarise.py` exits 0 on complete lines, counts a kind once per run, and exits 1 for a
  missing `REVIEWED` line, a repeated `FACTS` line, a run not in the plan, a run twice in
  the plan and a kind the reviewer does not judge.

It prints `ok <check>` or `FAIL <check>: <reason>` for each, and exits 1 when one fails.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, List, Optional

import yaml

EVALS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EVALS))

from facts import asked_files  # noqa: E402

PYTHON = sys.executable


class Context:
    """The suite under test and the folder the fake runs go in."""

    def __init__(self, python_dir: Path, skill: Path, scratch: Path) -> None:
        self.python_dir = python_dir
        self.skill = skill
        self.scratch = scratch


def fake_run(ctx: Context, name: str, case: str, skip: Optional[str] = None) -> Path:
    """Builds a kept run of a case that wrote every asked file except `skip`."""
    root = ctx.scratch / name
    workspace = root / "sealed" / "home" / "cwd"
    workspace.mkdir(parents=True)
    (root / "out").mkdir()
    prompt = (ctx.skill / "evals" / case / "prompt.md").read_text("utf-8")
    for file in asked_files(prompt):
        if file != skip:
            (workspace / file).write_text(f"# {file} written by the agent\n", "utf-8")
    trace = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "done"}]},
    }
    (root / "out" / "trace.jsonl").write_text(json.dumps(trace) + "\n", "utf-8")
    return root


def run_facts(
    ctx: Context, root: Path, case: str, out: Path, relative: bool = False
) -> subprocess.CompletedProcess:
    """Runs facts.py on a kept run; `relative` passes --python-dir relative to the folder it runs in."""
    return subprocess.run(
        [
            PYTHON,
            str(EVALS / "facts.py"),
            str(root),
            "--task",
            case,
            "--python-dir",
            ctx.python_dir.name if relative else str(ctx.python_dir),
            "--skill",
            str(ctx.skill),
            "--out",
            str(out),
            "--version",
            "a",
            "--model",
            "haiku",
            "--run",
            "1",
        ],
        capture_output=True,
        text=True,
        cwd=ctx.python_dir.parent if relative else None,
    )


def check_case(ctx: Context, case: str) -> List[str]:
    """Returns what is wrong with facts.py's folder for a full run of a case."""
    root = fake_run(ctx, f"run-{case}", case)
    out = ctx.scratch / f"review-{case}"
    done = run_facts(ctx, root, case, out)
    if done.returncode != 0:
        return [f"facts.py exited {done.returncode}: {done.stderr.strip()}"]
    wrong = []
    line = json.loads(done.stdout)
    if line.get("kind") != "FACTS" or line.get("task") != case:
        wrong.append(f"grade line is {line}")
    prompt = (ctx.skill / "evals" / case / "prompt.md").read_text("utf-8")
    for file in asked_files(prompt):
        kept = file + ".txt" if file.endswith((".py", ".sh")) else file
        if not (out / "files" / kept).is_file():
            wrong.append(f"files/{kept} not written")
    for part in ["trace.jsonl", "task/prompt.md", "task/answer.md", "skill/SKILL.md"]:
        if not (out / part).is_file():
            wrong.append(f"{part} not written")
    facts = json.loads((out / "facts.json").read_text("utf-8"))
    if facts["missing"]:
        wrong.append(f"missing lists {facts['missing']}")
    task = yaml.safe_load((EVALS / "tasks" / case / "task.yaml").read_text("utf-8"))
    profiles = task.get("profiles") or []
    if sorted(facts["odctl"]["explain"]) != sorted(profiles):
        wrong.append(
            f"explain covers {sorted(facts['odctl']['explain'])}, want {profiles}"
        )
    if not facts["odctl"]["list"]:
        wrong.append("list is empty")
    if profiles and not facts["odctl"]["compose"]:
        wrong.append("compose is empty")
    if profiles and not facts["odctl"].get("dry_run"):
        wrong.append("dry_run is empty")
    hidden = subprocess.run(
        [PYTHON, str(EVALS / "check_hidden.py"), str(out)],
        capture_output=True,
        text=True,
    )
    if hidden.returncode != 0:
        wrong.append(f"check_hidden.py found: {hidden.stdout.strip()}")
    return wrong


def check_missing_file(ctx: Context) -> List[str]:
    """A file the run did not write is listed in `missing`."""
    root = fake_run(ctx, "run-missing", "spark-kafka", skip="run.sh")
    out = ctx.scratch / "review-missing"
    done = run_facts(ctx, root, "spark-kafka", out)
    if done.returncode != 0:
        return [f"facts.py exited {done.returncode}"]
    missing = json.loads((out / "facts.json").read_text("utf-8"))["missing"]
    return [] if missing == ["run.sh"] else [f"missing is {missing}, want ['run.sh']"]


def check_fails_without(ctx: Context, what: str) -> List[str]:
    """facts.py exits 2 with no line when the transcript or the workspace is gone."""
    root = fake_run(ctx, f"run-no-{what}", "pg-tz")
    if what == "trace":
        (root / "out" / "trace.jsonl").unlink()
    else:
        shutil.rmtree(root / "sealed")
    done = run_facts(ctx, root, "pg-tz", ctx.scratch / f"review-no-{what}")
    if done.returncode != 2 or done.stdout.strip():
        return [
            f"exited {done.returncode} with output {done.stdout.strip()!r}, want 2 and none"
        ]
    return []


def check_fails_without_task(ctx: Context) -> List[str]:
    """facts.py exits 2 when the case has no task.yaml, here a case name with no tasks/ folder."""
    root = fake_run(ctx, "run-no-task", "pg-tz")
    case_copy = ctx.skill / "evals" / "selftest-no-task"
    shutil.copytree(ctx.skill / "evals" / "pg-tz", case_copy)
    try:
        done = run_facts(ctx, root, "selftest-no-task", ctx.scratch / "review-no-task")
    finally:
        shutil.rmtree(case_copy)
    if done.returncode != 2:
        return [f"exited {done.returncode}, want 2"]
    return []


def check_relative_python_dir(ctx: Context) -> List[str]:
    """facts.py works when --python-dir is relative to the folder it runs in."""
    root = fake_run(ctx, "run-relative", "pg-tz")
    done = run_facts(ctx, root, "pg-tz", ctx.scratch / "review-relative", relative=True)
    if done.returncode != 0:
        return [f"exited {done.returncode}: {done.stderr.strip()[-200:]}"]
    return []


def check_hidden_catches(ctx: Context) -> List[str]:
    """check_hidden.py exits 1 on a suite name and on an odctl version."""
    wrong = []
    for text in ["read <x>/suite-a/odctl/SKILL.md", "this is odctl 1.9.0"]:
        folder = ctx.scratch / f"planted-{len(text)}"
        folder.mkdir()
        (folder / "trace.jsonl").write_text(text + "\n", "utf-8")
        done = subprocess.run(
            [PYTHON, str(EVALS / "check_hidden.py"), str(folder)],
            capture_output=True,
            text=True,
        )
        if done.returncode != 1:
            wrong.append(f"{text!r}: exited {done.returncode}, want 1")
    return wrong


def check_summarise(ctx: Context) -> List[str]:
    """summarise.py on complete lines, and on each kind of wrong lines."""
    plan = ctx.scratch / "plan.tsv"
    plan.write_text("pg-tz\ta\thaiku\t1\nspark-kafka\ta\thaiku\t1\n", "utf-8")

    def line(task: str, kind: str, count: int = 0) -> str:
        return json.dumps(
            {
                "task": task,
                "kind": kind,
                "count": count,
                "version": "a",
                "model": "haiku",
                "run": "1",
            }
        )

    grades = [line("pg-tz", "FACTS"), line("spark-kafka", "FACTS")]
    reviews = [
        line("pg-tz", "A8", 1),
        line("pg-tz", "A8", 1),
        line("pg-tz", "REVIEWED"),
        line("spark-kafka", "REVIEWED"),
    ]

    def run(
        grade_lines: List[str], review_lines: List[str]
    ) -> subprocess.CompletedProcess:
        g = ctx.scratch / "g.jsonl"
        r = ctx.scratch / "r.jsonl"
        g.write_text("\n".join(grade_lines) + "\n", "utf-8")
        r.write_text("\n".join(review_lines) + "\n", "utf-8")
        return subprocess.run(
            [
                PYTHON,
                str(EVALS / "summarise.py"),
                "--plan",
                str(plan),
                "--grades",
                str(g),
                "--reviews",
                str(r),
            ],
            capture_output=True,
            text=True,
        )

    wrong = []
    done = run(grades, reviews)
    # Why: A8 is in one of two tasks, once, though the reviewer wrote it twice
    if done.returncode != 0 or "| A8 | 0.50 | 0.00 |" not in done.stdout:
        wrong.append(
            f"complete lines: exit {done.returncode}, output {done.stdout[:200]!r}"
        )
    bad = {
        "missing REVIEWED": (grades, reviews[:3]),
        "repeated FACTS": (grades + grades[:1], reviews),
        "run not in the plan": (grades, reviews + [line("feast-venv", "REVIEWED")]),
        "kind not judged": (grades, reviews + [line("pg-tz", "A5", 1)]),
        # Why: last, because it rewrites the plan the checks above read
        "run twice in the plan": (grades, reviews),
    }
    for name, (g, r) in bad.items():
        if name == "run twice in the plan":
            plan.write_text("pg-tz\ta\thaiku\t1\npg-tz\ta\thaiku\t1\nspark-kafka\ta\thaiku\t1\n", "utf-8")
        if run(g, r).returncode != 1:
            wrong.append(f"{name}: did not exit 1")
    return wrong


def main(argv: Optional[List[str]] = None) -> int:
    """Runs every check and prints its result.

    Args:
        argv: The command line without the program name; None reads `sys.argv`.

    Returns:
        0 when every check passes, else 1.
    """
    parser = argparse.ArgumentParser(
        description="Self-test of the evaluation's scripts."
    )
    parser.add_argument("--python-dir", type=Path, required=True)
    parser.add_argument("--skill", type=Path, required=True)
    args = parser.parse_args(argv)
    cases = sorted(
        p.name for p in (args.skill / "evals").iterdir() if (p / "prompt.md").is_file()
    )
    failed = False
    with tempfile.TemporaryDirectory() as scratch:
        ctx = Context(args.python_dir.resolve(), args.skill.resolve(), Path(scratch))
        checks: List[tuple] = [
            (f"facts {case}", lambda c=case: check_case(ctx, c)) for case in cases
        ]
        checks += [
            ("facts lists a missing file", lambda: check_missing_file(ctx)),
            (
                "facts fails with no transcript",
                lambda: check_fails_without(ctx, "trace"),
            ),
            (
                "facts fails with no workspace",
                lambda: check_fails_without(ctx, "workspace"),
            ),
            ("facts fails with no task.yaml", lambda: check_fails_without_task(ctx)),
            ("facts takes a relative --python-dir", lambda: check_relative_python_dir(ctx)),
            (
                "check_hidden catches a suite and a version",
                lambda: check_hidden_catches(ctx),
            ),
            ("summarise", lambda: check_summarise(ctx)),
        ]
        for name, check in checks:
            run: Callable[[], List[str]] = check
            wrong = run()
            if wrong:
                failed = True
                print(f"FAIL {name}: " + "; ".join(wrong))
            else:
                print(f"ok {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
