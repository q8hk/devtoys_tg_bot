from src.core.utils import text


def test_trim_and_normalize():
    raw = "  Hello\nWorld  "
    assert text.trim(raw) == "Hello\nWorld"
    assert text.normalize_whitespace(raw) == "Hello World"


def test_indent_and_dedent():
    content = "line1\n\nline2"
    indented = text.indent(content, prefix="--")
    assert indented.splitlines()[0].startswith("--")
    assert indented.splitlines()[1] == ""
    assert text.dedent("    foo\n        bar") == "foo\n    bar"


def test_slugify_and_case_conversions():
    slug = text.slugify("Héllo, World!")
    assert slug == "hello-world"
    assert text.to_upper("abc") == "ABC"
    assert text.to_lower("ABC") == "abc"


def test_line_helpers():
    content = "b\na\na"
    assert text.sort_lines(content) == "a\na\nb"
    assert text.unique_lines(content) == "b\na"
    numbered = text.add_line_numbers("alpha\nbeta", start=5, padding=2)
    assert numbered.splitlines()[0].startswith("05")
    assert text.strip_line_numbers(numbered) == "alpha\nbeta"


def test_lorem_generation_seeded():
    config = text.LoremConfig(words=5, seed=42)
    first = text.generate_lorem_ipsum(config)
    second = text.generate_lorem_ipsum(config)
    assert first == second
    assert first.endswith(".")
