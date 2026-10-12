"""ADR-0007, "Console scripts": one console script, named for the distribution,
with ``python -m l3io.wp.config`` kept working alongside it rather than instead.

Both entry points are RUN, not just declared: a declaration naming a function
that was renamed still builds, installs, and fails only when an operator types
the command. The console script is the one installed into this environment, so
this checks what ``uv sync`` built; ci.yml's verify-install job covers the wheel.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _project() -> dict[str, Any]:
    project: dict[str, Any] = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    return project


def _run(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)


def test_the_one_console_script_is_named_for_the_distribution() -> None:
    project = _project()
    assert list(project.get("scripts", {})) == [project["name"]], (
        f"[project.scripts] must declare exactly one script named {project['name']!r}; "
        f"found {list(project.get('scripts', {}))}"
    )


def test_the_console_script_target_exists() -> None:
    project = _project()
    module, _, attr = project["scripts"][project["name"]].partition(":")
    assert callable(getattr(importlib.import_module(module), attr, None)), (
        f"{module}:{attr} is not a callable"
    )


def test_both_entry_points_run_and_agree() -> None:
    name = _project()["name"]
    script = Path(sys.executable).parent / name
    assert script.exists(), f"{script} is not installed -- did uv sync run?"

    as_script = _run(str(script), "--help")
    as_module = _run(sys.executable, "-m", "l3io.wp.config", "--help")

    assert as_script.returncode == 0, as_script.stderr
    assert as_module.returncode == 0, as_module.stderr
    assert as_script.stdout == as_module.stdout
    assert as_script.stdout.strip(), "--help printed nothing"
