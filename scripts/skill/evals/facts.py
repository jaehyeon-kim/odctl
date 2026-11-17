"""Writes the folder the blind reviewer reads for one kept run, and one grade line.

Usage:

    <suite>/py/bin/python3.12 facts.py ROOT --task CASE --python-dir DIR --skill DIR
        --out DIR --version V --model M --run N

`ROOT` is a run folder that `claude plugin eval --keep-temp` kept: the agent's workspace is
`ROOT/sealed/home/cwd` and its full transcript `ROOT/out/trace.jsonl`. The command leaves both
unreadable, so `chmod 700 ROOT ROOT/sealed` comes first. `--python-dir` is the suite's
prepared Python, whose odctl is the version under test, and `--skill` the suite's skill copy.
Run the script with that Python, which has PyYAML.

The script measures nothing and judges nothing: every check that turns on what a command or a
file means is the reviewer's (`review_rubric.md`). It writes `--out`:

- `files/`: each file the case's prompt asks for, as the agent left it. A `.py` or `.sh` file
  gets `.txt` added, so that no tool of the repository runs or lints it.
- `trace.jsonl`: the run's full transcript.
- `task/`: the case's `prompt.md`, and `answer.md` from `tasks/CASE/`.
- `facts.json`: the files the prompt asks for that the run did not write (`missing`); and for
  the profiles of `tasks/CASE/task.yaml`, what odctl itself says about them, run from the
  suite's Python with no Docker: `odctl list --json` (`list`), `odctl explain <profile>
  --json` (`explain`), `odctl up <profiles> --dry-run` (`dry_run`), and from each of their
  compose files every service's container name, network aliases, ports, `expose` and whether
  it has a health check (`compose`), which the JSON leaves out.
- `skill/`: the skill copy's `SKILL.md` and `references/*.md`.

In every file the skill copy's path reads `<skill>`, the suite folder `<suite>`, the run
folder `<run>` and the odctl version the suite installs, such as `1.9.0` in odctl's own
output or in `TAG=1.9.0`, `<version>`, so that no text tells the version. `check_hidden.py` checks the result.

It prints one line, `{"task", "kind": "FACTS", "count": 0, "version", "model", "run"}`, which
`summarise.py` expects once per run. It exits 2, with no line, when the workspace, the
transcript, a case file or an odctl command it needs cannot be read or fails, because a fact
missing would read as a fact with nothing in it.
"""

import argparse
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

import yaml

HERE = Path(__file__).resolve().parent
# Why: a Python or shell file the reviewer reads is not run or linted by the repository's tools
RENAMED = (".py", ".sh")
# Why: odctl must answer as it does in a run, where no Docker can be reached
NO_DOCKER = "unix:///nonexistent/docker.sock"


class Failed(Exception):
    """A file or a command the facts need could not be read or failed."""


class Hide(NamedTuple):
    """A text replaced in what the reviewer reads, so that it does not tell the version."""

    old: str
    new: str


def hides_for(skill: Path, root: Path, version: str) -> List[Hide]:
    """Returns the replacements for the skill copy, its suite folder, the run folder and the
    odctl version.

    Each path is replaced in its given form, its resolved form and, for a path under
    `/private`, the form without it, which macOS prints for the same folder.
    """
    found = [Hide(version, "<version>")]
    for path, new in ((skill, "<skill>"), (skill.parent, "<suite>"), (root, "<run>")):
        for form in {str(path), str(path.resolve())}:
            found.append(Hide(form, new))
            if form.startswith("/private/"):
                found.append(Hide(form[len("/private") :], new))
    # Why: the longest first, so that a path is replaced before a part of it
    return sorted(found, key=lambda hide: -len(hide.old))


def hide_text(text: str, hides: List[Hide]) -> str:
    """Applies the replacements to a text."""
    for hide in hides:
        text = text.replace(hide.old, hide.new)
    return text


def copy_text(source: Path, target: Path, hides: List[Hide]) -> None:
    """Copies a text file with the replacements applied; a missing source fails."""
    if not source.is_file():
        raise Failed(f"cannot read {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(hide_text(source.read_text("utf-8", "replace"), hides), "utf-8")


def asked_files(prompt: str) -> List[str]:
    """Returns the names of the files a case's prompt asks for, in its order.

    They are the list items after the line "Write these files", each `- NAME: what it is`.
    """
    lines = prompt.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("Write these files")]
    if len(starts) != 1:
        raise Failed("the prompt has no single 'Write these files' line")
    names = []
    for line in lines[starts[0] + 1 :]:
        item = re.match(r"- ([^\s:]+):", line)
        if item:
            names.append(item.group(1))
        elif names and line.strip():
            break
    if not names:
        raise Failed("the prompt lists no file to write")
    return names


def odctl(python_dir: Path, args: List[str]) -> str:
    """Runs the suite's odctl in an empty folder with no Docker and returns its output."""
    env = {**os.environ, "DOCKER_HOST": NO_DOCKER, "NO_COLOR": "1", "COLUMNS": "200"}
    # Why: a workspace in the current folder would change what odctl reads
    with tempfile.TemporaryDirectory() as empty:
        done = subprocess.run(
            # Why: a relative --python-dir would otherwise be read from the empty folder
            [str(python_dir.resolve() / "bin" / "odctl"), *args],
            cwd=empty,
            env=env,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
    if done.returncode != 0:
        raise Failed(f"odctl {' '.join(args)} exited {done.returncode}: {done.stderr}")
    return done.stdout


def compose_facts(path: Path) -> Dict[str, dict]:
    """Returns each service of a compose file with the facts `odctl explain --json` leaves out."""
    if not path.is_file():
        raise Failed(f"cannot read {path}")
    services = (yaml.safe_load(path.read_text("utf-8")) or {}).get("services") or {}
    facts = {}
    for name, service in sorted(services.items()):
        networks = service.get("networks") or {}
        aliases: List[str] = []
        if isinstance(networks, dict):
            for network in networks.values():
                aliases += (network or {}).get("aliases") or []
        facts[name] = {
            "container_name": service.get("container_name"),
            "aliases": aliases,
            "ports": [str(port) for port in service.get("ports") or []],
            "expose": [str(port) for port in service.get("expose") or []],
            "healthcheck": "healthcheck" in service,
            "profiles": service.get("profiles") or [],
        }
    return facts


def odctl_facts(python_dir: Path, profiles: List[str]) -> dict:
    """Returns what the suite's odctl says about the profiles, and their compose files."""
    listed = json.loads(odctl(python_dir, ["list", "--json"]))
    explain = {
        profile: json.loads(odctl(python_dir, ["explain", profile, "--json"]))
        for profile in profiles
    }
    resources = sorted(python_dir.glob("lib/python3*/site-packages/odctl/resources"))
    if len(resources) != 1:
        raise Failed(
            f"wanted one odctl/resources under {python_dir}, found {len(resources)}"
        )
    compose = {}
    for profile, info in explain.items():
        name = Path(info["compose_file"]).name
        compose[name] = compose_facts(resources[0] / name)
    facts = {
        "list": [p for p in listed if not profiles or p["profile"] in profiles],
        "explain": explain,
        "compose": compose,
    }
    if profiles:
        facts["dry_run"] = odctl(python_dir, ["up", *profiles, "--dry-run"])
    return facts


def write_review(args: argparse.Namespace) -> None:
    """Writes the reviewer's folder, as the module docstring sets out."""
    workspace = args.root / "sealed" / "home" / "cwd"
    if not (workspace.is_dir() and os.access(workspace, os.R_OK | os.X_OK)):
        raise Failed(
            f"cannot read {workspace}; open the kept folder first with "
            f"`chmod 700 {args.root} {args.root / 'sealed'}`"
        )
    # Why: the script runs with the suite's Python, so this is the version under test
    hides = hides_for(args.skill, args.root, importlib.metadata.version("odctl"))
    case = args.skill / "evals" / args.task
    task = HERE / "tasks" / args.task
    out = args.out
    copy_text(args.root / "out" / "trace.jsonl", out / "trace.jsonl", hides)
    copy_text(case / "prompt.md", out / "task" / "prompt.md", hides)
    copy_text(task / "answer.md", out / "task" / "answer.md", hides)
    missing = []
    for name in asked_files((case / "prompt.md").read_text("utf-8")):
        kept = name + ".txt" if name.endswith(RENAMED) else name
        if (workspace / name).is_file():
            copy_text(workspace / name, out / "files" / kept, hides)
        else:
            missing.append(name)
    spec = task / "task.yaml"
    if not spec.is_file():
        raise Failed(f"cannot read {spec}")
    profiles = (yaml.safe_load(spec.read_text("utf-8")) or {}).get("profiles") or []
    facts = {"missing": missing, "odctl": odctl_facts(args.python_dir, profiles)}
    (out / "facts.json").write_text(
        hide_text(json.dumps(facts, indent=2, sort_keys=True), hides) + "\n", "utf-8"
    )
    copy_text(args.skill / "SKILL.md", out / "skill" / "SKILL.md", hides)
    for page in sorted((args.skill / "references").glob("*.md")):
        copy_text(page, out / "skill" / "references" / page.name, hides)


def main(argv: Optional[List[str]] = None) -> int:
    """Writes the reviewer's folder and prints the run's grade line.

    Args:
        argv: The command line without the program name; None reads `sys.argv`.

    Returns:
        0, or 2 when a file or a command the facts need failed.
    """
    parser = argparse.ArgumentParser(
        description="Writes the reviewer's folder of a run."
    )
    parser.add_argument("root", type=Path)
    parser.add_argument("--task", required=True)
    parser.add_argument("--python-dir", type=Path, required=True)
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--run", required=True)
    args = parser.parse_args(argv)
    try:
        write_review(args)
    except Failed as error:
        print(f"facts.py: {error}", file=sys.stderr)
        return 2
    line = {
        "task": args.task,
        "kind": "FACTS",
        "count": 0,
        "version": args.version,
        "model": args.model,
        "run": args.run,
    }
    print(json.dumps(line))
    return 0


if __name__ == "__main__":
    sys.exit(main())
