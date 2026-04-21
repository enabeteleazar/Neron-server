# tests/test_utils.py
# Tests pour core/utils.py

import pytest
from serverVNext.serverVNext.core.utils import (
    normalize_text,
    safe_get,
    truncate_text,
    validate_api_key_format,
    clean_filename,
    safe_json_loads,
    safe_json_dumps,
)


class TestNormalizeText:
    def test_basic_normalization(self):
        assert normalize_text("HÉllo WÖRLD") == "hello world"

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_whitespace(self):
        assert normalize_text("  hello  ") == "hello"

    def test_special_chars(self):
        assert normalize_text("café résumé") == "cafe resume"


class TestSafeGet:
    def test_nested_access(self):
        data = {"a": {"b": {"c": "value"}}}
        assert safe_get(data, "a", "b", "c") == "value"

    def test_missing_key(self):
        data = {"a": {"b": {}}}
        assert safe_get(data, "a", "b", "missing") is None

    def test_default_value(self):
        data = {"a": {"b": {}}}
        assert safe_get(data, "a", "b", "missing", default="default") == "default"

    def test_non_dict(self):
        data = "not a dict"
        assert safe_get(data, "key") is None


class TestTruncateText:
    def test_no_truncation(self):
        assert truncate_text("short", 10) == "short"

    def test_truncation(self):
        assert truncate_text("very long text here", 10) == "very long..."

    def test_custom_suffix(self):
        assert truncate_text("very long text", 8, "[...]") == "very[...]")


class TestValidateApiKeyFormat:
    def test_valid_keys(self):
        assert validate_api_key_format("abc123")
        assert validate_api_key_format("abc-123_def")
        assert validate_api_key_format("ABC123DEF")

    def test_invalid_keys(self):
        assert not validate_api_key_format("")
        assert not validate_api_key_format("key with spaces")
        assert not validate_api_key_format("key@with#special")


class TestCleanFilename:
    def test_clean_filename(self):
        assert clean_filename("file.py") == "file.py"
        assert clean_filename("file with spaces.py") == "file_with_spaces.py"
        assert clean_filename("file@#$%.py") == "file____.py"


class TestSafeJson:
    def test_safe_json_loads_valid(self):
        assert safe_json_loads('{"key": "value"}') == {"key": "value"}

    def test_safe_json_loads_invalid(self):
        assert safe_json_loads("invalid json") is None

    def test_safe_json_loads_default(self):
        assert safe_json_loads("invalid", default="default") == "default"

    def test_safe_json_dumps_valid(self):
        result = safe_json_dumps({"key": "value"})
        assert '"key": "value"' in result

    def test_safe_json_dumps_invalid(self):
        assert safe_json_dumps(set([1, 2, 3])) == "{}"