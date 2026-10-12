"""Every governing rule, and what enforces it here (docs/traceability.toml).

The rules this package obeys live in ``../l3io-wordpress-backup``: the AD-n
entries of ``ARCHITECTURE-SPINE.md`` and the ADRs under ``docs/adr/``. The table
carries one row per rule -- not only the ones that bind this package, because
"does it bind?" is a judgement, and a judgement belongs on a reviewed row rather
than inside a filter nobody reads.

Two layers, with different reach:

* **Everywhere, CI included:** the table is well formed, and every enforcer it
  names exists -- a test function, a named workflow step, or a file. A renamed
  test cannot leave a row pointing at nothing.
* **Only where the sibling repository is checked out:** the table's rule set
  equals the set derived from the governing documents, and each row's
  ``source_sha256`` matches the rule's current text. A CI runner has no sibling,
  so there this test is SKIPPED -- reported as skipped, never as passed. An added
  ADR or an amended rule is therefore caught on a developer machine, not in CI.

What none of this proves: that an enforcer actually enforces its rule. A row
saying ``AD-14 -> test_x`` is checked for test_x existing, not for test_x
being a good test of AD-14. That stays a review judgement.

The sibling is read from its COMMITTED tree (``git show HEAD:``), never its
working tree: reading a sibling's mid-change working tree as if it were the
specification is how ADR-0012's amendment came to exist.
"""

from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import tomllib
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TABLE = REPO_ROOT / "docs" / "traceability.toml"
SIBLING = REPO_ROOT.parent / "l3io-wordpress-backup"

SPINE_PATTERN = "_bmad-output/planning-artifacts/architecture/*/ARCHITECTURE-SPINE.md"
ADR_PATTERN = "docs/adr/[0-9][0-9][0-9][0-9]-*.md"

ID_RE = re.compile(r"^(AD-[1-9][0-9]*|ADR-[0-9]{4})$")
AD_HEADING_RE = re.compile(r"^### (AD-[0-9]+) ", re.MULTILINE)
SECTION_END_RE = re.compile(r"^#{1,3} ", re.MULTILINE)

#: A binding row must say how it is covered; one of these, at least.
COVERAGE_KEYS = ("enforced_by", "untested", "not_checkable")
KNOWN_KEYS = {"id", "source_sha256", "binds", "reason", "note", *COVERAGE_KEYS}


# ---- the table ---------------------------------------------------------------


def load_rows(path: Path = TABLE) -> list[dict[str, Any]]:
    with path.open("rb") as fh:
        rows: list[dict[str, Any]] = tomllib.load(fh).get("rule", [])
    return rows


def row_problems(row: dict[str, Any]) -> list[str]:
    """Structural defects in one row. Empty means well formed."""
    rid = row.get("id", "<no id>")
    problems = []
    if not ID_RE.match(str(rid)):
        problems.append(f"{rid}: id is not AD-n or ADR-nnnn")
    unknown = set(row) - KNOWN_KEYS
    if unknown:
        problems.append(f"{rid}: unknown key(s) {sorted(unknown)}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("source_sha256", ""))):
        problems.append(f"{rid}: source_sha256 missing or not a sha256 hex digest")
    binds = row.get("binds")
    if not isinstance(binds, bool):
        problems.append(f"{rid}: binds must be true or false")
    elif binds:
        if not any(row.get(k) for k in COVERAGE_KEYS):
            problems.append(
                f"{rid}: binds this package but names no enforcer and declares no "
                f"gap -- set enforced_by, untested or not_checkable"
            )
        if "reason" in row:
            problems.append(f"{rid}: 'reason' explains a non-binding rule; use 'note'")
    else:
        if not row.get("reason"):
            problems.append(f"{rid}: does not bind, but gives no reason")
        present = [k for k in COVERAGE_KEYS if k in row]
        if present:
            problems.append(f"{rid}: does not bind, yet carries {present}")
    return problems


# ---- enforcers ---------------------------------------------------------------


def _test_names(source: str) -> set[str]:
    """``func`` and ``Class::method`` for every test-named def in a module."""
    names = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.startswith("test"):
                names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.update(
                f"{node.name}::{item.name}"
                for item in node.body
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
                and item.name.startswith("test")
            )
    return names


def enforcer_problem(ref: str, root: Path = REPO_ROOT) -> str | None:
    """None if ``ref`` names something that exists, else what is wrong.

    Three shapes: ``tests/x.py::name`` (or ``::Class::name``), a workflow step
    ``.github/workflows/x.yml::job-id::step name``, or a bare repo path.
    """
    path_part, _, rest = ref.partition("::")
    path = root / path_part
    if not path.is_file():
        return f"{ref}: no such file {path_part}"
    if not rest:
        return None
    if path.suffix == ".py":
        if rest not in _test_names(path.read_text(encoding="utf-8")):
            return f"{ref}: no test named {rest} in {path_part}"
        return None
    if path.suffix in (".yml", ".yaml"):
        job_id, _, step = rest.partition("::")
        jobs = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("jobs", {})
        if job_id not in jobs:
            return f"{ref}: no job {job_id!r} in {path_part}"
        if step and step not in [s.get("name") for s in jobs[job_id].get("steps", [])]:
            return f"{ref}: job {job_id!r} has no step named {step!r}"
        return None
    return f"{ref}: cannot resolve '::' inside a {path.suffix or 'suffixless'} file"


# ---- the governing documents -------------------------------------------------


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ad_sections(spine: str) -> dict[str, str]:
    """Each ``### AD-n`` heading's text, through to the next heading of level <= 3."""
    sections = {}
    for match in AD_HEADING_RE.finditer(spine):
        end = SECTION_END_RE.search(spine, match.end())
        sections[match.group(1)] = spine[match.start() : end.start() if end else len(spine)]
    return sections


def governing_rules(files: dict[str, str]) -> dict[str, str]:
    """Rule id -> sha256 of its text, from a {repo-relative path: text} map.

    The scope is derived by pattern from whatever files exist, never listed by
    hand, so an ADR added later cannot escape it.
    """
    spines = [p for p in files if fnmatch(p, SPINE_PATTERN)]
    if len(spines) != 1:
        raise AssertionError(f"expected exactly one {SPINE_PATTERN}, found {spines}")
    rules = {rid: sha(text) for rid, text in ad_sections(files[spines[0]]).items()}
    if not rules:
        raise AssertionError(f"no '### AD-n' headings in {spines[0]}")
    for path, text in files.items():
        if fnmatch(path, ADR_PATTERN):
            rules[f"ADR-{Path(path).name[:4]}"] = sha(text)
    return rules


def drift(rows: list[dict[str, Any]], rules: dict[str, str]) -> list[str]:
    """How the table disagrees with the governing documents. Empty means none."""
    table = {row["id"]: row.get("source_sha256") for row in rows}
    out = [
        f"{rid}: in the governing documents, no row in the table"
        for rid in sorted(rules.keys() - table.keys())
    ]
    out += [
        f"{rid}: row in the table, no such rule in the governing documents"
        for rid in sorted(table.keys() - rules.keys())
    ]
    for rid in sorted(rules.keys() & table.keys()):
        if table[rid] != rules[rid]:
            out.append(
                f"{rid}: rule text changed since the row was reviewed -- re-read it, "
                f're-judge the row, then set source_sha256 = "{rules[rid]}"'
            )
    return out


def committed_files(repo: Path) -> dict[str, str]:
    """{path: text} for the spine and ADRs at the sibling's HEAD."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
        ).stdout

    paths = git("ls-tree", "-r", "--name-only", "HEAD").splitlines()
    wanted = [p for p in paths if fnmatch(p, SPINE_PATTERN) or fnmatch(p, ADR_PATTERN)]
    return {p: git("show", f"HEAD:{p}") for p in wanted}


# ---- the real table ----------------------------------------------------------


def test_the_table_is_not_empty() -> None:
    assert load_rows(), f"{TABLE} has no [[rule]] rows"


def test_every_row_is_well_formed() -> None:
    rows = load_rows()
    problems = [p for row in rows for p in row_problems(row)]
    ids = [str(row.get("id")) for row in rows]
    problems += [
        f"{rid}: appears more than once" for rid in sorted({i for i in ids if ids.count(i) > 1})
    ]
    assert not problems, "\n".join(problems)


def test_every_enforcer_exists() -> None:
    refs = [ref for row in load_rows() for ref in row.get("enforced_by", [])]
    assert refs, "no row names an enforcer -- the check below would pass vacuously"
    problems = [p for ref in refs if (p := enforcer_problem(ref))]
    assert not problems, "\n".join(problems)


@pytest.mark.skipif(
    not (SIBLING / ".git").exists(),
    reason=f"{SIBLING.name} is not checked out beside this repo -- the table cannot be "
    "compared with the governing documents here (expected on a CI runner)",
)
def test_the_table_matches_the_governing_documents() -> None:
    problems = drift(load_rows(), governing_rules(committed_files(SIBLING)))
    assert not problems, "\n".join(problems)


# ---- planted violations: each check must fail when it should ------------------

SPINE = "_bmad-output/planning-artifacts/architecture/a-2026/ARCHITECTURE-SPINE.md"
SPINE_TEXT = (
    "# Spine\n\n## Invariants\n\n"
    "### AD-1 — one\n\nbody one\n\n"
    "### AD-2 — two\n\nbody two\n\n"
    "## Next\n"
)


def _row(**over: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": "AD-1",
        "source_sha256": "0" * 64,
        "binds": True,
        "enforced_by": ["tests/test_traceability.py::test_the_table_is_not_empty"],
    }
    row.update(over)
    return row


def test_a_sound_row_has_no_problems() -> None:
    assert row_problems(_row()) == []
    no_cover = {
        k: v for k, v in _row(binds=False, reason="backup only").items() if k != "enforced_by"
    }
    assert row_problems(no_cover) == []


@pytest.mark.parametrize(
    ("row", "fragment"),
    [
        ({k: v for k, v in _row().items() if k != "enforced_by"}, "names no enforcer"),
        (_row(binds=False), "gives no reason"),
        (_row(binds=False, reason="x"), "yet carries"),
        (_row(id="AD-01"), "id is not"),
        (_row(source_sha256="abc"), "source_sha256"),
        (_row(binds="yes"), "binds must be"),
        (_row(enforced_bye=["x"]), "unknown key"),
    ],
)
def test_a_malformed_row_is_rejected(row: dict[str, Any], fragment: str) -> None:
    assert any(fragment in p for p in row_problems(row)), row_problems(row)


def test_a_declared_gap_satisfies_a_binding_row() -> None:
    gap = {k: v for k, v in _row(untested="no grep gate yet").items() if k != "enforced_by"}
    assert row_problems(gap) == []


def test_a_missing_test_is_reported() -> None:
    assert "no test named" in (
        enforcer_problem("tests/test_traceability.py::test_does_not_exist") or ""
    )
    assert "no such file" in (enforcer_problem("tests/test_nope.py::test_x") or "")


def test_a_helper_function_is_not_a_test() -> None:
    assert "no test named" in (enforcer_problem("tests/test_traceability.py::row_problems") or "")


def test_a_unittest_method_resolves() -> None:
    assert enforcer_problem("tests/test_config_string_get.py::GetTestCase::test_string") is None


def test_a_missing_workflow_job_or_step_is_reported() -> None:
    assert enforcer_problem(".github/workflows/ci.yml::contracts::architecture contracts") is None
    assert "no job" in (enforcer_problem(".github/workflows/ci.yml::nope::x") or "")
    assert "no step named" in (enforcer_problem(".github/workflows/ci.yml::contracts::nope") or "")


def test_the_derived_scope_reaches_an_adr_nobody_listed() -> None:
    files = {
        SPINE: SPINE_TEXT,
        "docs/adr/0099-planted.md": "# ADR-0099\n",
        "docs/adr/README.md": "index",
    }
    rules = governing_rules(files)
    assert set(rules) == {"AD-1", "AD-2", "ADR-0099"}, "README.md must not count; 0099 must"


def test_the_derived_scope_finds_the_spine_under_any_architecture_folder() -> None:
    moved = SPINE.replace("a-2026", "renamed-folder-2027")
    assert set(governing_rules({moved: SPINE_TEXT})) == {"AD-1", "AD-2"}


def test_a_missing_or_duplicated_spine_fails_loudly() -> None:
    with pytest.raises(AssertionError, match="exactly one"):
        governing_rules({"docs/adr/0001-x.md": "x"})
    with pytest.raises(AssertionError, match="exactly one"):
        governing_rules({SPINE: SPINE_TEXT, SPINE.replace("a-2026", "b"): SPINE_TEXT})


def test_an_ad_section_ends_at_the_next_heading() -> None:
    sections = ad_sections(SPINE_TEXT)
    assert sections["AD-1"].endswith("body one\n\n")
    assert "## Next" not in sections["AD-2"]


def test_drift_reports_added_removed_and_edited_rules() -> None:
    rules = governing_rules({SPINE: SPINE_TEXT, "docs/adr/0001-x.md": "one"})
    rows = [{"id": rid, "source_sha256": digest} for rid, digest in rules.items()]
    assert drift(rows, rules) == []

    added = drift(rows[:-1], rules)
    assert any("ADR-0001: in the governing documents" in p for p in added)

    removed = drift([*rows, {"id": "AD-30", "source_sha256": "0" * 64}], rules)
    assert any("AD-30: row in the table, no such rule" in p for p in removed)

    edited = governing_rules(
        {SPINE: SPINE_TEXT.replace("body one", "body ONE"), "docs/adr/0001-x.md": "one"}
    )
    assert [p for p in drift(rows, edited) if p.startswith("AD-1:")], (
        "an edit to AD-1 must be reported"
    )
