# Running the evaluation

This file holds the main session's steps, from the suite to the result table. `claude plugin eval` makes the runs, each in an empty folder inside its OS sandbox; `facts.py` writes the facts of each kept run; a blind Opus reviewer judges every kind against `review_rubric.md`; and `summarise.py` makes the table. Nothing under `scripts/skill/evals/` is shipped: `scripts/gen_pages.py` writes only `skills/odctl/`.

`<scratch>` is a folder outside every repository. Each use of `claude plugin eval` starts nested Claude runs and needs the owner's approval.

## Before any counted run

1. The self-test passes: `<scratch>/suite-a/py/bin/python3.12 scripts/skill/evals/selftest/selftest.py --python-dir <scratch>/suite-a/py --skill <scratch>/suite-a/odctl` prints `ok` for every check and exits 0.
2. The review cases hold. `python3 scripts/skill/evals/review_cases/check.py --prepare <scratch>/rc --skill <scratch>/suite-a/odctl` writes each case of `review_cases/` into `<scratch>/rc/<case>/` as the reviewer reads it. Two fresh Opus reviewers each read every one of those folders as step 7 sets out, and each saves its replies as `<scratch>/rc-a/<case>.jsonl` and `<scratch>/rc-b/<case>.jsonl`. Then `check.py --reviews <scratch>/rc-a <scratch>/rc-b` finds no difference: each reviewer gives the known right counts, and the two find the same kinds in the runs whose counts are not known.
3. One trial run confirms the setup end to end: one case on each model, steps 2 to 8 below.

## Steps

1. Create the folders the steps write into: `mkdir -p <scratch>/tree-a <scratch>/results <scratch>/review <scratch>/grades <scratch>/reviews`, with one `tree-` folder per version. Build the suite of each version from a copy of the repository at that version, into a folder whose name does not tell the version: `git archive <tag> | tar -x -C <scratch>/tree-a`, then `uv run --no-project python scripts/skill/evals/make_suite.py --tree <scratch>/tree-a --out <scratch>/suite-a`. Write down which suite is which in `<scratch>/versions.txt`; no file the reviewer reads names it. `make_suite.py` builds and installs with `--offline`, so uv's cache must already hold `hatchling`, the wheel's dependencies and `pytest`: run `uv sync` (which includes the `dev` group, where `pytest` is) and `uv build` once in the repository, online, before the first suite.
2. Run the cases from the suite's folder (`cd <scratch>/suite-a`), once per model:

   ```bash
   claude plugin eval ./odctl --model haiku --runs 1 --ablation none -j 3 \
     --scaffold --keep-temp --allow-tools Bash Write Edit --no-publish --trust-plugin \
     --case '<glob>' --output-dir <scratch>/results/a-haiku \
     --report <scratch>/results/a-haiku.html --json <scratch>/results/a-haiku.json
   ```

   `-j 3` keeps at most three runs going at once. `--output-dir` and `--report` keep the results outside the skill copy, which every later run can read. A run that ends on the 5-hour usage limit or the 80-turn limit has an error, is not graded, and runs again with `--case <case>`.
3. Back in the repository's folder, list the kept runs of each result file: `python3 scripts/skill/evals/kept_runs.py <scratch>/results/a-haiku.json --version a`. Each line is the task, the version, the run number and the kept folder `<root>`. For a run with an error the script prints `-` and the error in place of the folder and exits 1; that run is not graded.
4. Open each kept folder, which the command leaves at mode 500 with `sealed/` at 000: `chmod 700 <root> <root>/sealed`. Run nothing inside it, because a tool that reads its configuration from the folder would run the agent's files.
5. Write the facts of each run, giving it the next number `<n>` of a counter. Append `<n>`, the task, the version, the model and the run number to `<scratch>/review/index.tsv`, and the task, version, model and run to `<scratch>/plan.tsv`; no reviewer reads either:

   ```bash
   <scratch>/suite-a/py/bin/python3.12 scripts/skill/evals/facts.py <root> --task <task> \
     --python-dir <scratch>/suite-a/py --skill <scratch>/suite-a/odctl \
     --out <scratch>/review/<n> --version <version> --model <model> --run <run> \
     >> <scratch>/grades/<version>-<model>.jsonl
   ```

   It exits 2 with no line when a file or a command it needs fails, and removes what it wrote of `--out`; that run's facts are written again once the cause is fixed. It also exits 2 when `--out` already exists, so that no file of another run stays in it.
6. `python3 scripts/skill/evals/check_hidden.py <scratch>/review/*` prints nothing and exits 0: no file names a suite or an odctl version.
7. Start one fresh Opus reviewer per folder (`model: opus`), at most three at a time, with this message, where `<rubric>` is the path of `review_rubric.md` and `<folder>` is `<scratch>/review/<n>`:

   ```text
   Read <rubric> in full. Then read every file of the folder <folder> as it sets out, including trace.jsonl in full, and judge the run against it. Run nothing and change no file. Reply with the JSON lines the rubric's Output section sets out, and nothing else.
   ```

   Save the reply as `<scratch>/reviews/<n>.jsonl`, setting on each line the task, version, model and run that `index.tsv` gives for `<n>`, in place of any the reviewer wrote.
8. Make the table: `python3 scripts/skill/evals/summarise.py --plan <scratch>/plan.tsv --grades <scratch>/grades/*.jsonl --reviews <scratch>/reviews/*.jsonl`. It exits 1 and lists each run with a line missing or repeated, or not in the plan; such a run's facts are written or its review is made again, after its old lines are removed.
