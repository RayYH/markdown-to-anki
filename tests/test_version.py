"""Guard against __version__ drifting from pyproject.toml."""

import re
from pathlib import Path

from click.testing import CliRunner

from markdown_to_anki import __version__
from markdown_to_anki.cli import cli


def _pyproject_version() -> str:
    text = (Path(__file__).parent.parent / "pyproject.toml").read_text()
    m = re.search(r'^version = "([^"]+)"', text, re.M)
    assert m, "version line not found in pyproject.toml"
    return m.group(1)


def test_version_matches_pyproject():
    # Skip when running against an installed wheel where pyproject.toml
    # may not sit next to the tests (e.g. in CI installing the built sdist).
    if not (Path(__file__).parent.parent / "pyproject.toml").exists():
        return
    assert __version__ == _pyproject_version()


def test_cli_version_flag():
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_version_subcommand():
    result = CliRunner().invoke(cli, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == __version__
