"""PHP 8.4 grades the scanner: what the package reads and writes is what PHP runs.

Read-back re-scans with the scanner's own patterns, so it cannot see the scanner's
bugs. Two shipped that way: salts cut short at the first ``);``, and defines inside
a block comment read as live. Every check here asks PHP instead. The ``php_read``
fixture in ``conftest.py`` skips without docker, or fails under
``L3IO_REQUIRE_PHP_ORACLE=1``.
"""

from __future__ import annotations

import random
from typing import Any

from tests.test_real_configs import CASES, EXPECTED, rewrite

from l3io.wp.config import ConfigWriteError, ReadBackError, WpConfigString
from l3io.wp.config.domain.values import ConfigValue

RANDOM_CASES = 300

# Dense in what has broken this scanner or could: quotes and escapes, the `);` and
# `;` that ended values early, comment markers, PHP's `$` and `?>`, and non-ASCII.
_ALPHABET = "abcXYZ019 _-.:/'\\\"();,#*?<>$@!%&=+[]{}|~`^\té€✓"


def _same(php: Any, ours: ConfigValue) -> bool:
    """Equal, and the same PHP type: `true` is not `1`, and `1` is not `1.0`."""
    return type(php) is type(ours) and php == ours


def _problems(case: str, seen: dict[str, Any]) -> list[str]:
    expected = EXPECTED[case]
    constants: dict[str, Any] = seen["constants"]
    out = [f"{case}: PHP warned: {w}" for w in seen["warnings"]]
    out += [
        f"{case}: {key} is {constants.get(key, '<undefined>')!r} to PHP, {value!r} expected"
        for key, value in expected["values"].items()
        if key not in constants or not _same(constants[key], value)
    ]
    out += [f"{case}: PHP does not define {key}" for key in expected["raw"] if key not in constants]
    out += [
        f"{case}: PHP defines {key}, expected absent"
        for key in expected["absent"]
        if key in constants
    ]
    unread = constants.keys() - expected["values"].keys() - expected["raw"].keys()
    out += [f"{case}: PHP defines {key}, which the package does not read" for key in sorted(unread)]
    if seen["table_prefix"] != expected["table_prefix"]:
        out.append(f"{case}: $table_prefix is {seen['table_prefix']!r} to PHP")
    return out


def test_the_expectations_are_what_php_reads(php_read):
    """expected.json, which the docker-free tests rely on, is PHP's reading, not ours."""
    seen = php_read(CASES)
    assert [p for case in CASES for p in _problems(case, seen[case])] == []


def test_php_reads_every_rewrite_where_the_package_wrote_it(php_read):
    rewrites = {case: rewrite(case) for case in CASES}
    before = php_read(CASES)
    after = php_read({case: content for case, (content, _, _) in rewrites.items()})
    problems: list[str] = []
    for case, (_content, written, prefix) in rewrites.items():
        seen = after[case]
        constants = seen["constants"]
        problems += [f"{case}: PHP warned: {w}" for w in seen["warnings"]]
        problems += [
            f"{case}: wrote {key}={value!r}, PHP reads {constants.get(key, '<undefined>')!r}"
            for key, value in written.items()
            if key not in constants or not _same(constants[key], value)
        ]
        # Literals only: an expression such as `WP_HOME . '/content'` rightly follows
        # a constant that was written.
        problems += [
            f"{case}: {key} changed, and it was not written"
            for key, value in before[case]["constants"].items()
            if key not in written
            and key not in EXPECTED[case]["raw"]
            and constants.get(key) != value
        ]
        if EXPECTED[case]["table_prefix_literal"] and seen["table_prefix"] != prefix:
            problems.append(
                f"{case}: wrote $table_prefix={prefix!r}, PHP reads {seen['table_prefix']!r}"
            )
    assert problems == []


def _random_text(rng: random.Random) -> str:
    return "".join(rng.choice(_ALPHABET) for _ in range(rng.randint(0, 40)))


def test_random_writes_land_as_php_reads_them(php_read):
    """Whenever ``set()`` returns, PHP reads exactly what was written.

    300 configs, from WordPress's sample in both line endings. A write the package
    refuses is allowed; a write it accepts and PHP reads differently is the defect.
    Seeded, so a failure reproduces.
    """
    rng = random.Random(20261029)  # noqa: S311 - test data, seeded to reproduce, not secrets
    bases = [CASES["wordpress-sample"].decode(), CASES["wordpress-sample-lf"].decode()]
    cases: dict[str, bytes] = {}
    intended: dict[str, tuple[dict[str, ConfigValue], str]] = {}
    for n in range(RANDOM_CASES):
        config = WpConfigString(bases[n % 2])
        values: dict[str, ConfigValue] = {
            "DB_PASSWORD": _random_text(rng),
            "AUTH_KEY": _random_text(rng),
            "WP_DEBUG": rng.random() < 0.5,
            "WP_POST_REVISIONS": rng.randint(-(2**63), 2**63 - 1),
            "WP_REDIS_TIMEOUT": rng.uniform(-1e6, 1e6),
            "L3IO_RANDOM": _random_text(rng),
        }
        prefix = _random_text(rng)
        try:
            for key, value in values.items():
                config.set(key, value)
            config.set_variable("table_prefix", prefix)
        except (ConfigWriteError, ReadBackError):  # pragma: no cover - none today
            continue
        cases[f"r{n:03d}"] = config.content.encode()
        intended[f"r{n:03d}"] = (values, prefix)
    assert len(cases) == RANDOM_CASES, "every random write was accepted"

    seen = php_read(cases)
    problems = [
        f"{name}: wrote {key}={value!r}, "
        f"PHP reads {seen[name]['constants'].get(key, '<undefined>')!r}"
        for name, (values, _) in intended.items()
        for key, value in values.items()
        if not _same(seen[name]["constants"].get(key), value)
    ]
    problems += [
        f"{name}: wrote $table_prefix={prefix!r}, PHP reads {seen[name]['table_prefix']!r}"
        for name, (_, prefix) in intended.items()
        if seen[name]["table_prefix"] != prefix
    ]
    problems += [f"{name}: PHP warned: {w}" for name in cases for w in seen[name]["warnings"]]
    assert problems == [], f"{len(problems)} disagreements, first: {problems[:5]}"
