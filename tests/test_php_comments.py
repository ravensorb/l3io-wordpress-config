"""What PHP does not execute, the scanner must not read: comments, and `define` in any case.

v0.1.1 masked only a comment that began a line (`//`, `#`, or a ` * ` docblock line).
A plain line inside a multi-line ``/* ... */`` was read as live, so a commented-out
old ``DB_NAME`` above the live one was the value returned, and a write to a key
that existed only inside a comment edited the comment and reported success. PHP
function names are case-insensitive, so ``DEFINE('X', ...)`` is a definition the
scanner did not see, and ``set()`` added a second one. Each expectation below is
what PHP 8.4 reads; ``tests/test_php_oracle.py`` checks that against PHP itself.
"""

import pytest

from l3io.wp.config import MISSING, WpConfigFile, WpConfigString

BLOCK_BEFORE = "<?php\n/*\ndefine( 'DB_NAME', 'old' );\n*/\ndefine( 'DB_NAME', 'live' );\n"
BLOCK_AFTER = "<?php\ndefine( 'DB_NAME', 'live' );\n/*\ndefine( 'DB_NAME', 'old' );\n*/\n"
BLOCK_ONLY = "<?php\n/*\ndefine( 'WP_CACHE', true );\n*/\ndefine( 'DB_NAME', 'live' );\n"


def test_a_define_inside_a_block_comment_is_not_read():
    assert WpConfigString(BLOCK_BEFORE).get("DB_NAME") == "live"
    assert WpConfigString(BLOCK_ONLY).get("WP_CACHE") is MISSING


def test_a_write_reaches_the_live_define_not_the_commented_one():
    config = WpConfigString(BLOCK_BEFORE)
    assert config.set("DB_NAME", "new") is True
    assert "define( 'DB_NAME', 'old' );" in config.content, "the comment is not touched"
    assert config.get("DB_NAME") == "new"


def test_a_key_only_in_a_comment_is_added_as_live():
    config = WpConfigString(BLOCK_ONLY)
    config.set("WP_CACHE", False)
    assert "define( 'WP_CACHE', true );" in config.content, "the comment is not touched"
    assert "define('WP_CACHE', false);" in config.content
    assert config.get("WP_CACHE") is False


@pytest.mark.parametrize("content", [BLOCK_BEFORE, BLOCK_AFTER], ids=["before", "after"])
def test_a_commented_copy_is_not_a_duplicate(tmp_path, content):
    """Read-back counted the commented copy and refused a sound write."""
    path = tmp_path / "wp-config.php"
    path.write_text(content)
    assert WpConfigFile(path).set("DB_NAME", "new") is True
    assert WpConfigFile(path).get("DB_NAME") == "new"


def test_a_variable_inside_a_block_comment_is_not_read():
    content = "<?php\n/*\n$table_prefix = 'old_';\n*/\n$table_prefix = 'wp_';\n"
    assert WpConfigString(content).get_variable("table_prefix") == "wp_"


def test_an_apostrophe_inside_a_comment_does_not_open_a_string():
    """WordPress's own sample: `/* That's all, stop editing! */` precedes ABSPATH."""
    content = "<?php\n/* That's all, stop editing! */\ndefine( 'DB_NAME', 'live' );\n"
    assert WpConfigString(content).get("DB_NAME") == "live"


def test_comment_markers_inside_a_string_open_nothing():
    """A salt can hold `/*`; inside a quoted value it is data, not a comment."""
    content = "<?php\ndefine( 'AUTH_KEY', 'a/*b' );\ndefine( 'DB_NAME', 'live' );\n"
    config = WpConfigString(content)
    assert config.get("AUTH_KEY") == "a/*b"
    assert config.get("DB_NAME") == "live"


@pytest.mark.parametrize("marker", ["//", "#"])
def test_a_block_marker_inside_a_line_comment_opens_nothing(marker):
    content = f"<?php\n{marker} see /* below\ndefine( 'DB_NAME', 'live' );\n"
    assert WpConfigString(content).get("DB_NAME") == "live"


def test_a_block_comment_ends_at_the_first_close_even_after_a_quote():
    """Quotes mean nothing inside a comment, so `*/` after one still closes it."""
    content = "<?php\n/* 'unclosed */\ndefine( 'DB_NAME', 'live' );\n"
    assert WpConfigString(content).get("DB_NAME") == "live"


def test_an_unterminated_block_comment_hides_everything_after_it():
    """PHP rejects the file outright; the scanner at least reads nothing past it."""
    content = "<?php\ndefine( 'DB_USER', 'u' );\n/*\ndefine( 'DB_NAME', 'x' );\n"
    config = WpConfigString(content)
    assert config.get("DB_USER") == "u"
    assert config.get("DB_NAME") is MISSING


@pytest.mark.parametrize("spelling", ["DEFINE", "Define", "dEfInE"])
def test_define_is_read_in_any_case(spelling):
    assert WpConfigString(f"<?php\n{spelling}('DB_NAME', 'a');\n").get("DB_NAME") == "a"


def test_an_uppercase_define_is_updated_in_place():
    config = WpConfigString("<?php\nDEFINE('DB_NAME','a');\n")
    config.set("DB_NAME", "b")
    assert config.content == "<?php\nDEFINE('DB_NAME','b');\n"
