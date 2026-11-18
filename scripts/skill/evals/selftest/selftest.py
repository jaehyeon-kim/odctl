"""Shows that the evaluation's scripts work before any counted run (run_task.md, step 1).

Usage:

    <suite>/py/bin/python3.12 selftest.py --python-dir <suite>/py --skill <suite>/odctl

It builds kept runs by hand in a temporary folder, in the layout `claude plugin eval
--keep-temp` leaves (`ROOT/sealed/home/cwd` and `ROOT/out/trace.jsonl`), and checks:

- `facts.py` on a run of every case writes each file the prompt asks for, the transcript, the
  task files and the skill, lists no missing file, and gives the explain, compose and dry-run
  facts of every profile in the case's `task.yaml`; and `check_hidden.py` passes on the result.
- A file the run did not write is listed in `missing`, and `facts.py` works with a relative
  `--python-dir`, and with a relative `--skill` without replacing every period.
- `facts.py` exits 2 with no line when the transcript, the workspace or the case's
  `task.yaml` cannot be read, because a fact that reads nothing must fail, not count nothing;
  and when `--out` already exists, so that no file of another run stays in it, leaving the
  first run's folder as it was.
- `facts.py` removes what it wrote of `--out` when odctl is missing and when the case's
  `prompt.md` is not UTF-8, which fail only after it wrote the transcript, and a second run
  into the same `--out` then works.
- `check_hidden.py` exits 1 when a file names a suite or an odctl version, and 2 when a
  folder it is given is not a folder, holds no file, or holds a file or a folder that cannot
  be read.
- `review_cases/check.py` finds no kind on a line whose `count` is 0, and reports each line
  whose `count` is not the number 1, or that is not a JSON object.
- `summarise.py` exits 0 on complete lines, counts a kind once per run, and exits 1 for a
  missing `REVIEWED` line, a repeated `FACTS` line, a run not in the plan, a run twice in
  the plan and a kind the reviewer does not judge.

It prints `ok <check>` or `FAIL <check>: <reason>` for each, and exits 1 when one fails.
"""

import argparse
import gzip
import json
import os
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

sys.path.insert(0, str(EVALS / "review_cases"))

from check import _found  # noqa: E402

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
    ctx: Context,
    root: Path,
    case: str,
    out: Path,
    relative: bool = False,
    relative_skill: bool = False,
    skill: Optional[Path] = None,
) -> subprocess.CompletedProcess:
    """Runs facts.py on a kept run; `relative` passes --python-dir, and `relative_skill`
    --skill, relative to the suite folder it then runs in; `skill` replaces the suite's."""
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
            # Why: the skill need not sit next to the venv
            os.path.relpath(ctx.skill, ctx.python_dir.parent)
            if relative_skill
            else str(skill or ctx.skill),
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
        cwd=ctx.python_dir.parent if relative or relative_skill else None,
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
    tests = [
        service["healthcheck_test"]
        for services in facts["odctl"]["compose"].values()
        for service in services.values()
        if service["healthcheck"]
    ]
    if not all(tests):
        wrong.append("a service with a health check has no healthcheck_test")
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


def check_relative_skill(ctx: Context) -> List[str]:
    """facts.py with a relative --skill does not replace each period with `<suite>`."""
    root = fake_run(ctx, "run-relative-skill", "pg-tz")
    out = ctx.scratch / "review-relative-skill"
    done = run_facts(ctx, root, "pg-tz", out, relative_skill=True)
    if done.returncode != 0:
        return [f"exited {done.returncode}: {done.stderr.strip()[-200:]}"]
    prompt = (out / "task" / "prompt.md").read_text("utf-8")
    if "<suite>" in prompt or "reply.md" not in prompt:
        return [f"task/prompt.md has periods replaced: {prompt[:120]!r}"]
    return []


def check_existing_out(ctx: Context) -> List[str]:
    """facts.py exits 2 when --out already holds another run's folder."""
    out = ctx.scratch / "review-existing"
    first = run_facts(
        ctx, fake_run(ctx, "run-existing-1", "spark-kafka"), "spark-kafka", out
    )
    if first.returncode != 0:
        return [f"first run exited {first.returncode}"]
    root = fake_run(ctx, "run-existing-2", "spark-kafka", skip="run.sh")
    done = run_facts(ctx, root, "spark-kafka", out)
    if done.returncode != 2 or done.stdout.strip():
        return [
            f"second run into the same --out exited {done.returncode} with output "
            f"{done.stdout.strip()!r}, want 2 and none"
        ]
    # Why: the second run skipped run.sh, so a write into the folder would show here
    missing = json.loads((out / "facts.json").read_text("utf-8"))["missing"]
    if not (out / "files" / "run.sh.txt").is_file() or missing != []:
        return [f"the first run's folder changed: missing is {missing}"]
    return []


def check_missing_odctl(ctx: Context) -> List[str]:
    """facts.py exits 2 and removes its part-written --out when bin/odctl is missing."""
    no_odctl = ctx.scratch / "venv-without-odctl"
    no_odctl.mkdir(exist_ok=True)
    out = ctx.scratch / "review-missing-odctl"
    root = fake_run(ctx, "run-missing-odctl", "pg-tz")
    done = subprocess.run(
        [
            PYTHON,
            str(EVALS / "facts.py"),
            str(root),
            *("--task", "pg-tz", "--python-dir", str(no_odctl)),
            *("--skill", str(ctx.skill), "--out", str(out)),
            *("--version", "a", "--model", "haiku", "--run", "1"),
        ],
        capture_output=True,
        text=True,
    )
    if done.returncode != 2 or out.exists() or done.stdout.strip():
        return [
            f"exited {done.returncode} with --out left {out.exists()}, want 2 and "
            f"removed: {done.stderr.strip()[-200:]}"
        ]
    # Why: odctl runs only after the transcript and task/ are written, so a failure that
    # names it shows that a part-written folder was removed
    if "bin/odctl" not in done.stderr:
        return [f"failed before odctl ran: {done.stderr.strip()[-200:]}"]
    return []


def check_bad_prompt(ctx: Context) -> List[str]:
    """facts.py exits 2 and removes --out when a case's prompt.md is not UTF-8, and a second
    run into the same --out then works."""
    skill = ctx.scratch / "skill-bad-prompt"
    shutil.copytree(ctx.skill, skill)
    with (skill / "evals" / "pg-tz" / "prompt.md").open("ab") as f:
        f.write(b"\xff\n")
    root = fake_run(ctx, "run-bad-prompt", "pg-tz")
    out = ctx.scratch / "review-bad-prompt"
    done = run_facts(ctx, root, "pg-tz", out, skill=skill)
    if done.returncode != 2 or out.exists() or done.stdout.strip():
        return [
            f"exited {done.returncode} with --out left {out.exists()} and output "
            f"{done.stdout.strip()!r}, want 2, removed and none: "
            f"{done.stderr.strip()[-200:]}"
        ]
    # Why: prompt.md is copied into --out before it is read strictly
    if "UnicodeDecodeError" not in done.stderr:
        return [f"failed before prompt.md was read: {done.stderr.strip()[-200:]}"]
    again = run_facts(ctx, root, "pg-tz", out)
    if again.returncode != 0:
        return [
            f"the second run exited {again.returncode}: {again.stderr.strip()[-200:]}"
        ]
    return []


def check_hidden_needs_folders(ctx: Context) -> List[str]:
    """check_hidden.py exits 2 for a name that is no folder, a file, a folder with no file,
    a gzip file cut short and a folder it cannot list."""
    a_file = ctx.scratch / "not-a-folder.txt"
    a_file.write_text("text\n", "utf-8")
    # Why: a folder that holds only a folder still holds no file
    (ctx.scratch / "no-file" / "inner").mkdir(parents=True)
    cut = ctx.scratch / "cut-gzip"
    cut.mkdir()
    (cut / "trace.jsonl.gz").write_bytes(gzip.compress(b"odctl 1.9.0\n")[:15])
    closed = ctx.scratch / "closed"
    (closed / "inner").mkdir(parents=True)
    (closed / "a.txt").write_text("text\n", "utf-8")
    (closed / "inner" / "b.txt").write_text("odctl 1.9.0\n", "utf-8")
    (closed / "inner").chmod(0)
    wrong = []
    try:
        for path in [
            ctx.scratch / "no-such-folder",
            a_file,
            ctx.scratch / "no-file",
            cut,
            closed,
        ]:
            done = subprocess.run(
                [PYTHON, str(EVALS / "check_hidden.py"), str(path)],
                capture_output=True,
                text=True,
            )
            if done.returncode != 2:
                wrong.append(f"{path.name}: exited {done.returncode}, want 2")
    finally:
        # Why: the temporary folder is removed at the end, which needs the mode back
        (closed / "inner").chmod(0o700)
    return wrong


def check_counts(ctx: Context) -> List[str]:
    """review_cases/check.py finds no kind on a line with count 0, as summarise.py scores it,
    and reports each line whose count is not the number 1 or that is not a JSON object."""
    reviewed = {"task": "pg-tz", "kind": "REVIEWED", "count": 0}
    cases = [
        # (the kind's line, whether the kind is found, the problems wanted)
        ({"task": "pg-tz", "kind": "A8", "count": 1}, True, 0),
        ({"task": "pg-tz", "kind": "A8", "count": 0}, False, 1),
        ({"task": "pg-tz", "kind": "A8", "count": -1}, False, 1),
        ({"task": "pg-tz", "kind": "A8", "count": True}, True, 1),
        ({"task": "pg-tz", "kind": "A8", "count": "1"}, True, 1),
        ({"task": "pg-tz", "kind": "A8", "count": 1.0}, True, 1),
        (["A8", 1], False, 1),
    ]
    wrong = []
    for number, (row, found, wanted) in enumerate(cases):
        reply = ctx.scratch / f"count-{number}.jsonl"
        reply.write_text(json.dumps(row) + "\n" + json.dumps(reviewed) + "\n", "utf-8")
        try:
            kinds, problems = _found(reply)
        except Exception as error:
            wrong.append(f"{row!r}: raised {type(error).__name__}")
            continue
        if bool(kinds) != found or len(problems) != wanted:
            wrong.append(
                f"{row!r}: found {sorted(kinds)} with problems {problems}, want "
                f"{'A8' if found else 'no kind'} and {wanted} problem"
            )
    return wrong


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
            plan.write_text(
                "pg-tz\ta\thaiku\t1\npg-tz\ta\thaiku\t1\nspark-kafka\ta\thaiku\t1\n",
                "utf-8",
            )
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
            (
                "facts takes a relative --python-dir",
                lambda: check_relative_python_dir(ctx),
            ),
            ("facts takes a relative --skill", lambda: check_relative_skill(ctx)),
            ("facts refuses an existing --out", lambda: check_existing_out(ctx)),
            ("facts cleans up when odctl is missing", lambda: check_missing_odctl(ctx)),
            (
                "facts cleans up when prompt.md is not UTF-8",
                lambda: check_bad_prompt(ctx),
            ),
            (
                "check_hidden catches a suite and a version",
                lambda: check_hidden_catches(ctx),
            ),
            (
                "check_hidden refuses a folder it cannot search",
                lambda: check_hidden_needs_folders(ctx),
            ),
            ("check.py checks each count", lambda: check_counts(ctx)),
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
