"""
Record what PHP 8.4 reads in each corpus case, as tests/fixtures/wp-config/expected.json.

Run after adding or changing a fixture, then review the diff before committing it:

    uv run python tools/record_corpus_expectations.py > tests/fixtures/wp-config/expected.json

Every expectation is PHP's reading, never this package's. A key is a *literal* when
every ``define('KEY', <source>)`` spelled for it has literal source (a single-quoted
string, ``true``/``false``, or a number), and its expected value is PHP's, so a
commented-out literal copy cannot satisfy it. Any other key is *raw*: the package
returns the live source text, and PHP must merely define it. *Absent* keys are those
spelled in a ``define()`` somewhere that PHP does not define: the commented-out ones.

``tests/test_php_oracle.py::test_the_expectations_are_what_php_reads`` fails if the
file and PHP ever disagree, so a hand edit cannot drift from PHP unnoticed. Needs
docker. The patterns below are deliberately not the package's: the point is a
reading that does not share its code.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.conftest import _LOOP, PHP_IMAGE, _archive  # noqa: E402
from tests.test_real_configs import corpus  # noqa: E402

LITERAL = re.compile(r"^(?:'(?:[^'\\]|\\.)*'|(?i:true|false)|[+-]?\d+(?:\.\d+)?)$")
VALUE = r"""(?:'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|[^'"\n])*?"""
DEFINE = re.compile(r"(?i:define)\s*\(\s*'([A-Za-z_]\w*)'\s*,\s*(" + VALUE + r")\s*\)\s*;")
PREFIX = re.compile(r"^\$table_prefix\s*=\s*(.*?)\s*;", re.MULTILINE)


def record(cases: dict[str, bytes]) -> dict[str, dict[str, Any]]:
    done = subprocess.run(  # noqa: S603 - fixed argv; the configs arrive on stdin
        ["docker", "run", "--rm", "-i", "--network", "none", PHP_IMAGE, "sh", "-c", _LOOP],  # noqa: S607
        input=_archive(cases),
        capture_output=True,
        check=True,
    )
    php = {}
    for line in done.stdout.decode().splitlines():
        name, _, report = line.partition("\t")
        php[name] = json.loads(report)

    out: dict[str, dict[str, Any]] = {}
    for case, data in sorted(cases.items()):
        text = data.decode("utf-8")
        seen = php[case]
        if seen["warnings"]:
            msg = f"{case}: PHP warned, so the fixture is not a sound config: {seen['warnings']}"
            raise SystemExit(msg)
        sources: dict[str, list[str]] = {}
        for m in DEFINE.finditer(text):
            sources.setdefault(m.group(1), []).append(m.group(2).strip())
        values: dict[str, Any] = {}
        raw: dict[str, str] = {}
        for key, value in seen["constants"].items():
            spelled = sources.get(key, [])
            if spelled and all(LITERAL.match(s) for s in spelled):
                values[key] = value
                continue
            expressions = [s for s in spelled if not LITERAL.match(s)]
            if len(expressions) != 1:
                msg = f"{case}: cannot tell which source of {key} is live: {spelled}"
                raise SystemExit(msg)
            raw[key] = expressions[0]
        prefix = PREFIX.search(text)
        out[case] = {
            "values": values,
            "raw": raw,
            "absent": sorted(sources.keys() - seen["constants"].keys()),
            "table_prefix": seen["table_prefix"],
            "table_prefix_literal": bool(prefix and LITERAL.match(prefix.group(1))),
        }
    return out


if __name__ == "__main__":
    json.dump(record(corpus()), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
