"""
Architecture contract tests.

Each derives its scope by walking the package rather than from a hand-kept list,
so a module added later cannot quietly escape the rule.
"""

import ast
import pathlib
import re
from collections.abc import Iterator

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "src"
NAMESPACE = "wp"
PACKAGE = SRC / "l3io" / NAMESPACE / "config"

# A rename that misses this file must FAIL, not skip. The path used to be built
# from separate quoted segments, so a search-and-replace over "l3io/wp" never
# reached it: PACKAGE silently pointed at a directory that did not exist, the
# parametrised AD-1 tests got an empty parameter set and pytest SKIPPED them, and
# the AD-27 assertion below started checking a path that cannot exist. Ten tests
# vanished with zero failures.
assert PACKAGE.is_dir(), f"PACKAGE does not exist: {PACKAGE} — did the namespace change?"

INWARD_ONLY = ("core", "domain")
OUTWARD_LAYERS = ("ports", "adapters", "cli")


def _modules(*relative: str) -> Iterator[pathlib.Path]:
    for part in relative:
        found = sorted((PACKAGE / part).rglob("*.py"))
        assert found, f"no modules under {PACKAGE / part} — an empty scope skips, not fails"
        yield from found


def test_no_init_marker_at_either_namespace_level():
    """
    AD-27: an `__init__.py` at l3io/ or l3io/wp/ makes this a regular package,
    shadows the PEP 420 namespace, and makes the sibling distributions
    unimportable -- while this package's own tests still pass.
    """
    assert not (SRC / "l3io" / "__init__.py").exists()
    assert not (SRC / "l3io" / NAMESPACE / "__init__.py").exists()


def test_the_only_init_files_live_at_or_below_the_area_package():
    found = {p.relative_to(SRC).as_posix() for p in SRC.rglob("__init__.py")}
    escaped = {p for p in found if not p.startswith("l3io/wp/config/")}
    assert not escaped, f"__init__.py outside the area package: {escaped}"


@pytest.mark.parametrize("module", list(_modules(*INWARD_ONLY)), ids=lambda p: p.name)
def test_the_functional_core_imports_no_outward_layer(module):
    """AD-1: core/ and domain/ never import ports/, adapters/ or cli/."""
    tree = ast.parse(module.read_text(), filename=str(module))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    for name in imported:
        for layer in OUTWARD_LAYERS:
            assert f"l3io.wp.config.{layer}" not in name, (
                f"{module.name} imports {name}, which is outward of it"
            )


@pytest.mark.parametrize("module", list(_modules(*INWARD_ONLY)), ids=lambda p: p.name)
def test_the_functional_core_performs_no_io(module):
    """
    AD-1 again. An import-linter contract cannot see builtins, so `open` is
    checked here by AST rather than assumed covered.
    """
    forbidden_modules = {"os", "pathlib", "shutil", "subprocess", "socket", "tempfile"}
    tree = ast.parse(module.read_text(), filename=str(module))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden_modules, (
                    f"{module.name} imports the I/O module {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden_modules, (
                f"{module.name} imports from the I/O module {node.module}"
            )
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "open", f"{module.name} calls open()"


def test_the_package_declares_no_runtime_dependencies():
    """AD-2: zero runtime dependencies, permanently."""
    import tomllib

    pyproject = REPO / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())
    assert data["project"]["dependencies"] == []


# ---- AD-4 and AD-10: rules that bind every module below the composition root ----

#: The composition roots. Everything else in the package is a library module.
COMPOSITION_ROOTS = ("cli",)
ROOT_MODULES = ("__main__.py",)


def _library_modules() -> list[pathlib.Path]:
    found = sorted(
        p
        for p in PACKAGE.rglob("*.py")
        if p.relative_to(PACKAGE).parts[0] not in (*COMPOSITION_ROOTS, *ROOT_MODULES)
    )
    assert found, f"no library modules under {PACKAGE} -- an empty scope skips, not fails"
    return found


DRY_RUN_RE = re.compile(r"dry_?run|what_?if", re.IGNORECASE)


def dry_run_mentions(source: str) -> list[str]:
    """AD-4's grep gate: every line naming a Dry Run flag, in any spelling."""
    return [line.strip() for line in source.splitlines() if DRY_RUN_RE.search(line)]


#: Configuring logging is the composition root's job (AD-10); a library only asks
#: for a logger. These names configure, wherever they are called from.
LOGGING_CONFIGURERS = {"basicConfig", "dictConfig", "fileConfig", "addHandler", "setLevel"}


def logging_violations(source: str) -> list[str]:
    """AD-10, for a library module. Empty means compliant."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            names += [a.name for a in node.names] if isinstance(node, ast.Import) else []
            if isinstance(node, ast.ImportFrom):
                names += [f"{node.module}.{a.name}" for a in node.names]
            for name in names:
                if name.split(".")[0] == "structlog":
                    out.append(f"imports {name}: AD-10 keeps structlog out of this package")
                if name == "logging.config" or name.startswith("logging.config."):
                    out.append(f"imports {name}: only a composition root configures logging")
                if name.rsplit(".", 1)[-1] in LOGGING_CONFIGURERS and name.startswith("logging"):
                    out.append(f"imports {name}: only a composition root configures logging")
        elif isinstance(node, ast.Call):
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if called in LOGGING_CONFIGURERS:
                out.append(f"calls {called}(): only a composition root configures logging")
            if called == "getLogger" and not (
                len(node.args) == 1
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "__name__"
                and not node.keywords
            ):
                out.append("calls getLogger() with something other than __name__")
    return out


@pytest.mark.parametrize(
    "module", _library_modules(), ids=lambda p: p.as_posix().split("/config/")[-1]
)
def test_no_library_module_names_a_dry_run_flag(module):
    """
    AD-4: Dry Run is adapter selection, never a conditional, so no module below a
    composition root may mention one. This package has no Dry Run today, so the
    gate passes trivially -- it exists to catch one being added inside core/ or
    adapters/.
    """
    assert not dry_run_mentions(module.read_text()), dry_run_mentions(module.read_text())


@pytest.mark.parametrize(
    "module", _library_modules(), ids=lambda p: p.as_posix().split("/config/")[-1]
)
def test_no_library_module_configures_logging(module):
    """
    AD-10: library modules emit through ``logging.getLogger(__name__)`` and never
    configure logging; cli/ is the composition root and may. A handler added
    here would duplicate every record in the host application's stream.
    """
    assert not logging_violations(module.read_text()), logging_violations(module.read_text())


def test_the_composition_root_is_excluded_and_nothing_else():
    """The exclusion must not grow silently: only cli/ and __main__.py are roots."""
    library = {p.relative_to(PACKAGE).parts[0] for p in _library_modules()}
    assert {"core", "domain", "adapters", "ports"} <= library
    assert not library & {*COMPOSITION_ROOTS, *ROOT_MODULES}


@pytest.mark.parametrize(
    "source",
    [
        "if dry_run:\n    pass\n",
        "def run(*, whatIf=False): ...\n",
        "DRYRUN = True\n",
    ],
)
def test_the_dry_run_gate_catches_every_spelling(source):
    assert dry_run_mentions(source)


@pytest.mark.parametrize(
    ("source", "fragment"),
    [
        ("import structlog\n", "structlog"),
        ("from structlog import get_logger\n", "structlog"),
        ("import logging\nlogging.basicConfig()\n", "basicConfig"),
        ("from logging import basicConfig\n", "basicConfig"),
        ("import logging.config\n", "logging.config"),
        ("import logging\nlogging.getLogger().addHandler(h)\n", "addHandler"),
        ("from logging import getLogger\n_log = getLogger('l3io')\n", "other than __name__"),
        ("from logging import getLogger\n_log = getLogger()\n", "other than __name__"),
    ],
)
def test_the_logging_gate_catches_a_planted_violation(source, fragment):
    assert any(fragment in v for v in logging_violations(source)), logging_violations(source)


def test_the_logging_gate_accepts_the_compliant_shape():
    assert logging_violations("from logging import getLogger\n_log = getLogger(__name__)\n") == []
