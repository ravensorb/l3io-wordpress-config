"""Where a value ends: quoted strings are atomic (ADR-0010).

The value pattern used to end at the first ``)`` + ``;`` (or, for a variable, the
first ``;``), inside a quoted string or not. WordPress's own salt generator emits
both characters, so 3 of 320 salts sampled from api.wordpress.org on 2026-10-12 --
7.5% of salt sets -- were cut short, and ``set()`` on one wrote a PHP syntax error
that read-back passed, because read-back re-scans with the same patterns.

So these tests never grade the parser with the parser. Expected content is built
from a template, and generated values have a known true reading.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from l3io.wp.config import MISSING, WpConfigFile, WpConfigString
from l3io.wp.config.core.config_string import render_value

#: Three real salts from api.wordpress.org that the old pattern misread.
REAL_SALTS = {
    "NONCE_SALT": "vwP770a+em:+OeEP*i%peodLA+GY1l~P^3LY%?$Mp1FAXVVx?Ok);6YMW9hU2-E$",
    "SECURE_AUTH_SALT": "xms51OS}tW>C?wr]y+2K$ `Zp~gJTau0J-~K1Z-Btl ):3);xcr8d;f?KM|Y_$ob",
    "AUTH_SALT": "-w^Pk);Ie}S=S(aos{:-6KL+P0FzER=-(#]03f92EVDcS%K^/,l+fM~Z,aF7E`pC",
}

#: The sequences that end, or appear to end, a PHP value. Drawn as whole tokens:
#: drawn one character at a time, `)` and `;` are rarely adjacent, and a property
#: over them then passes over the defect it exists for. It did.
DELIMITERS = [");", ") ;", "');", "';", "\\'", "\\\\", '"', "(", ")", ";", ",", "$", " "]

#: One line of anything printable, dense in the sequences that delimit PHP.
VALUES = st.lists(
    st.characters(codec="utf-8", exclude_categories=("Cc", "Cs")) | st.sampled_from(DELIMITERS),
    max_size=40,
).map("".join)


def _define_file(value: str) -> str:
    """WordPress's own layout, with neighbours on both sides and on the same line."""
    return (
        "<?php\n"
        "define( 'BEFORE', 'b' );\n"
        f"define( 'K',        {render_value('K', value)} ); define( 'SAME_LINE', 's' );\n"
        "define( 'AFTER', 'a' );\n"
    )


def _variable_file(value: str) -> str:
    return f"<?php\n$before = 'b';\n$k = {render_value('k', value)};\n$after = 'a';\n"


@pytest.mark.parametrize(("key", "salt"), REAL_SALTS.items())
def test_a_real_wordpress_salt_reads_whole(key: str, salt: str) -> None:
    config = WpConfigString(f"<?php\ndefine( '{key}', '{salt}' );\ndefine( 'NEXT', 'n' );\n")
    assert config.get(key) == salt
    assert config.get("NEXT") == "n"


@pytest.mark.parametrize(("key", "salt"), REAL_SALTS.items())
def test_writing_over_a_real_salt_replaces_all_of_it(key: str, salt: str, tmp_path) -> None:
    path = tmp_path / "wp-config.php"
    path.write_text(f"<?php\ndefine( '{key}', '{salt}' );\n", encoding="utf-8")
    WpConfigFile(path).set(key, "new")
    assert path.read_text(encoding="utf-8") == f"<?php\ndefine( '{key}', 'new' );\n"


@given(VALUES)
def test_any_define_value_reads_back_exactly(value: str) -> None:
    config = WpConfigString(_define_file(value))
    assert config.get("K") == value
    assert (config.get("BEFORE"), config.get("AFTER")) == ("b", "a")
    # A second statement on one line is invisible by design (README: statements
    # start a line). The write properties below hold its text byte-identical.
    assert config.get("SAME_LINE") is MISSING


@given(VALUES, VALUES)
def test_any_define_write_changes_only_its_own_value(old: str, new: str) -> None:
    config = WpConfigString(_define_file(old))
    config.set("K", new)
    assert config.content == _define_file(new)


@given(VALUES)
def test_any_variable_value_reads_back_exactly(value: str) -> None:
    config = WpConfigString(_variable_file(value))
    assert config.get_variable("k") == value
    assert (config.get_variable("before"), config.get_variable("after")) == ("b", "a")


@given(VALUES, VALUES)
def test_any_variable_write_changes_only_its_own_value(old: str, new: str) -> None:
    config = WpConfigString(_variable_file(old))
    config.set_variable("k", new)
    assert config.content == _variable_file(new)


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(old=VALUES, new=VALUES)
def test_a_file_write_of_any_value_verifies_and_lands(old: str, new: str, tmp_path) -> None:
    path = tmp_path / "wp-config.php"
    path.write_text(_define_file(old), encoding="utf-8")
    WpConfigFile(path).set("K", new)
    assert path.read_text(encoding="utf-8") == _define_file(new)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("define( 'X', \"a);b\" );", '"a);b"'),  # double-quoted: raw text, but whole
        ("define('ABSPATH', dirname(__FILE__) . '/');", "dirname(__FILE__) . '/'"),
        (
            "define( 'WP_HOME', 'https://' . $_SERVER['HTTP_HOST'] );",
            "'https://' . $_SERVER['HTTP_HOST']",
        ),
        ("define('X', foo());", "foo()"),
        ("define('X', 'a\\');b');", "a');b"),
    ],
)
def test_an_expression_or_double_quoted_value_spans_to_its_own_close(
    line: str, expected: str
) -> None:
    config = WpConfigString(f"<?php\n{line}\n")
    assert config.get("X" if "'X'" in line else line.split("'")[1]) == expected


def test_a_double_quoted_value_is_replaced_whole() -> None:
    config = WpConfigString("<?php\ndefine( 'X', \"a);b\" );\n")
    config.set("X", "new")
    assert config.content == "<?php\ndefine( 'X', 'new' );\n"


def test_a_semicolon_inside_a_variable_string_is_part_of_it() -> None:
    assert WpConfigString("<?php\n$a = 'x;y';\n").get_variable("a") == "x;y"


def test_only_a_file_scope_variable_is_read() -> None:
    """An assignment indented inside a function body is not the file-scope one."""
    content = "<?php\nfunction f() {\n    $table_prefix = 'inner_';\n}\n$table_prefix = 'wp_';\n"
    assert WpConfigString(content).get_variable("table_prefix") == "wp_"


def test_an_indented_define_is_still_read() -> None:
    """WP-CLI's template writes WP_DEBUG inside an `if ( ! defined(...) )` block."""
    content = "<?php\nif ( ! defined( 'WP_DEBUG' ) ) {\n\tdefine( 'WP_DEBUG', false );\n}\n"
    assert WpConfigString(content).get("WP_DEBUG") is False
