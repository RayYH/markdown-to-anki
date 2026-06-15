#!/usr/bin/env bash
# Bump version, commit, tag. Pushing the tag is left to the operator;
# the release workflow (.github/workflows/release.yml) runs on `v*` push.
#
# Usage:  scripts/release.sh <new-version>
#         scripts/release.sh 0.1.6

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <new-version>   (e.g. 0.1.6 or 0.1.6rc1)" >&2
  exit 1
fi

new_version="$1"

# PEP 440 subset: N.N.N with optional aN/bN/rcN/.postN/.devN suffix.
if ! [[ "$new_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+|\.post[0-9]+|\.dev[0-9]+)?$ ]]; then
  echo "Version must look like 0.1.6, 0.1.6rc1, 0.1.6.post1, etc." >&2
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if ! git diff-index --quiet HEAD --; then
  echo "Working tree has uncommitted changes. Commit or stash first." >&2
  exit 1
fi

tag="v$new_version"
if git rev-parse --verify --quiet "refs/tags/$tag" >/dev/null; then
  echo "Tag $tag already exists." >&2
  exit 1
fi

# Update pyproject.toml in place (portable across BSD/GNU sed).
python3 - "$new_version" <<'PY'
import re, sys
path = "pyproject.toml"
text = open(path).read()
new_text, n = re.subn(
    r'^version = "[^"]+"',
    f'version = "{sys.argv[1]}"',
    text, count=1, flags=re.M,
)
if n != 1:
    sys.exit("Could not find `version = \"...\"` line in pyproject.toml")
open(path, "w").write(new_text)
PY

# Re-pin the lockfile so build artifacts match.
uv lock

git add pyproject.toml uv.lock
git commit -m "chore: release $tag"
git tag -a "$tag" -m "$tag"

echo
echo "Tagged $tag locally on $(git rev-parse --abbrev-ref HEAD)."
echo "To trigger the release workflow:"
echo "  git push origin $(git rev-parse --abbrev-ref HEAD) $tag"
