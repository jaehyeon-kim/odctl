#!/usr/bin/env bash
# Builds this version of the docs and pushes it to gh-pages as `latest`. Run by the
# docs job of pipeline.yml, from a checkout with the full history, because mike
# pulls the gh-pages branch.
set -euo pipefail

# Commit as the owner, so the gh-pages history adds no bot contributor.
git config --global user.name "jaehyeon-kim"
git config --global user.email "1023748+jaehyeon-kim@users.noreply.github.com"

# The version string from pyproject.toml
VERSION=$(grep -m 1 '^version = ' pyproject.toml | cut -d '"' -f 2)
echo "Extracted version: $VERSION"

# Runs on main wait in the pipeline's concurrency group, so a newer commit can
# reach main while this run is going. Deploying this run's commit would then
# publish older docs as `latest` until the next run deploys. This run deploys the
# head of main instead. That head has not passed this run's checks, so it is built
# in strict mode first. The head's unit tests and lint run in its own run, which
# deploys again only if they pass.
git fetch --quiet origin main
if [ "$(git rev-parse FETCH_HEAD)" != "$(git rev-parse HEAD)" ]; then
  echo "$(git rev-parse --short HEAD) is not the head of main ($(git rev-parse --short FETCH_HEAD)), so the head's docs are deployed."
  git checkout --quiet --detach FETCH_HEAD
  VERSION=$(grep -m 1 '^version = ' pyproject.toml | cut -d '"' -f 2)
  echo "Extracted version: $VERSION"
  DISABLE_MKDOCS_2_WARNING=true \
    uv run mkdocs build --strict --site-dir "$RUNNER_TEMP/strict-site"
fi

# The docs are deployed per minor version, so a patch release replaces its minor's
# docs instead of adding a copy of the site: the docs of 1.9.1 replace those of
# 1.9.0 under 1.9. The full version is an alias of the minor, so a link that
# names it still opens the docs.
DOCS_VERSION=$(echo "$VERSION" | cut -d . -f 1,2)
echo "Docs version: $DOCS_VERSION"

# A release of this minor deployed under its full version is replaced by the
# minor, which takes over its name and its aliases as aliases. mike delete
# removes a version with its aliases, so the names are kept first. Each line
# holds one such version, then its aliases other than `latest`.
old_names=()
while read -r -a names; do
  uv run mike delete "${names[0]}"
  old_names+=("${names[@]}")
done < <(uv run mike list --json | uv run python -c '
import json, sys
minor = sys.argv[1]
for v in json.load(sys.stdin):
    if v["version"] != minor and ".".join(v["version"].split(".")[:2]) == minor:
        print(" ".join([v["version"], *(a for a in v["aliases"] if a != "latest")]))
' "$DOCS_VERSION")

# Deploy the minor version and tag it as 'latest'. mike adds these aliases to
# those the minor already has, so the full version of an earlier patch stays.
# The + form expands an empty list to nothing under set -u in bash 3.2 too.
uv run mike deploy --update-aliases "$DOCS_VERSION" "$VERSION" latest ${old_names[@]+"${old_names[@]}"}

# The root of the site opens latest.
uv run mike set-default latest

# GitHub Pages answers every missing path under the site with the 404.html
# at the root of gh-pages, but mike writes one into each version folder
# only. Copy this version's page to the root. Its links point at latest/,
# so it renders at any depth.
git worktree add "$RUNNER_TEMP/gh-pages" gh-pages
cp "$RUNNER_TEMP/gh-pages/$DOCS_VERSION/404.html" "$RUNNER_TEMP/gh-pages/404.html"
# Assistants look for llms.txt at the root of the site. Its links already
# point at latest/, so the copy works from there.
cp "$RUNNER_TEMP/gh-pages/$DOCS_VERSION/llms.txt" "$RUNNER_TEMP/gh-pages/llms.txt"
cp "$RUNNER_TEMP/gh-pages/$DOCS_VERSION/llms-full.txt" "$RUNNER_TEMP/gh-pages/llms-full.txt"
git -C "$RUNNER_TEMP/gh-pages" add 404.html llms.txt llms-full.txt
git -C "$RUNNER_TEMP/gh-pages" diff --cached --quiet || git -C "$RUNNER_TEMP/gh-pages" commit -m "Root 404 page and llms.txt from $DOCS_VERSION"
# mike commits to the local gh-pages branch (after updating it from the remote),
# so everything above goes out in one push and starts one Pages build.
git -C "$RUNNER_TEMP/gh-pages" push origin gh-pages
