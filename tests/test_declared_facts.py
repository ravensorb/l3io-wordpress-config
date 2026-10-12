"""Facts declared once in pyproject.toml must agree with every place that restates them.

Ported from l3io-wordpress-database's tests/test_declared_facts.py (its FR-48 section),
whose functions are kept verbatim so the two can be diffed. That file's other two
checks are not ported: this package has no optional extras, so no
MissingDependencyError, and its CI runs no console script against the wheel (see
test_entry_points.py for the script itself). Ported, both would fail as vacuous.

Each check derives the set it examines from the tree -- every workflow -- never from
a hand-kept list, and asserts that set is non-empty before asserting the rule over it.

- ADR-0009: the supported-Python set. ``requires-python`` and the
  ``Programming Language :: Python :: 3.x`` classifiers are the declaration; every
  workflow matrix with a ``python`` axis restates it.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import yaml
from packaging.specifiers import SpecifierSet
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

#: Matrix axis names that carry a Python version.
PYTHON_AXES = ("python", "python-version")

_CLASSIFIER = re.compile(r"^Programming Language :: Python :: (3\.\d+)$")
_FROM_JSON = re.compile(r"fromJSON\('(\[[^']*\])'\)")


def _project() -> dict[str, Any]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        project: dict[str, Any] = tomllib.load(fh)["project"]
    return project


# ---------------------------------------------------------------- ADR-0009


def declared_pythons(project: dict[str, Any]) -> set[str]:
    return {m.group(1) for c in project["classifiers"] if (m := _CLASSIFIER.match(c))}


def _matrix_values(value: Any) -> set[str]:
    """Every version a matrix axis can take, including inside an act-collapse expression.

    ci.yml writes its axes as ``${{ vars.LOCAL_ACT && fromJSON('[...]') || fromJSON('[...]') }}``,
    so the full set is the union of every ``fromJSON`` list in the expression.
    """
    if isinstance(value, list):
        return {str(v) for v in value}
    if isinstance(value, str):
        found = _FROM_JSON.findall(value)
        if found:
            return {str(v) for blob in found for v in json.loads(blob)}
    msg = f"unrecognised matrix value {value!r}; teach this check to read it"
    raise AssertionError(msg)


def python_matrices(workflows: Path) -> dict[str, set[str]]:
    """``{"file.yml:job": versions}`` for every job whose matrix has a Python axis."""
    found: dict[str, set[str]] = {}
    for workflow in sorted(workflows.glob("*.y*ml")):
        document = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
        for job_id, job in (document.get("jobs") or {}).items():
            matrix = ((job or {}).get("strategy") or {}).get("matrix") or {}
            if not isinstance(matrix, dict):
                continue
            for axis in PYTHON_AXES:
                if axis in matrix:
                    found[f"{workflow.name}:{job_id}"] = _matrix_values(matrix[axis])
    return found


def matrix_mismatches(workflows: Path, expected: set[str]) -> list[str]:
    return [
        f"{where} runs {sorted(got)}, classifiers declare {sorted(expected)}"
        for where, got in python_matrices(workflows).items()
        if got != expected
    ]


def test_classifiers_agree_with_requires_python() -> None:
    project = _project()
    declared = declared_pythons(project)
    assert declared, "no Python 3.x classifiers -- the checks below would compare against nothing"
    spec = SpecifierSet(project["requires-python"])
    outside = sorted(v for v in declared if Version(v) not in spec)
    assert not outside, f"classifiers {outside} fall outside requires-python {spec}"
    floor = min(declared, key=Version)
    major, minor = floor.split(".")
    below = f"{major}.{int(minor) - 1}"
    assert Version(below) not in spec, (
        f"requires-python {spec} admits {below}, but the lowest classifier is {floor}: "
        "either the floor or the classifiers are wrong"
    )


def test_every_python_matrix_matches_the_classifiers() -> None:
    expected = declared_pythons(_project())
    matrices = python_matrices(WORKFLOWS)
    assert matrices, "no workflow has a Python matrix -- this guard is vacuous"
    assert not matrix_mismatches(WORKFLOWS, expected)


def test_a_matrix_in_an_unlisted_workflow_is_caught(tmp_path: Path) -> None:
    """Scope attack: a new workflow nobody told the check about."""
    (tmp_path / "anything-new.yaml").write_text(
        "on: push\njobs:\n  j:\n    strategy:\n      matrix:\n"
        "        python-version: ['3.11', '3.12']\n",
        encoding="utf-8",
    )
    assert matrix_mismatches(tmp_path, {"3.11", "3.12", "3.13"}) == [
        "anything-new.yaml:j runs ['3.11', '3.12'], classifiers declare ['3.11', '3.12', '3.13']"
    ]


def test_the_act_collapse_expression_is_read_in_full(tmp_path: Path) -> None:
    """Both branches of the LOCAL_ACT expression count, so the GitHub set is checked."""
    (tmp_path / "ci.yml").write_text(
        "on: push\njobs:\n  j:\n    strategy:\n      matrix:\n        python: >-\n"
        "          ${{ vars.LOCAL_ACT && fromJSON('[\"3.11\"]')\n"
        '              || fromJSON(\'["3.11","3.14"]\') }}\n',
        encoding="utf-8",
    )
    assert python_matrices(tmp_path) == {"ci.yml:j": {"3.11", "3.14"}}
