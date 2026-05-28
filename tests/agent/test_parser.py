import json

from src.agent.parser import ToolCallParser


def _parser() -> ToolCallParser:
    return ToolCallParser()


def test_returns_none_for_incomplete_json():
    assert _parser().parse('{"name": "read_file"') is None


def test_returns_none_for_plain_text_tokens():
    assert _parser().parse("Let me help you with that.") is None


def test_returns_none_for_empty_string():
    assert _parser().parse("") is None


def test_returns_tool_call_for_complete_json_block():
    raw = json.dumps({"name": "read_file", "arguments": {"path": "src/main.py"}})
    result = _parser().parse(raw)
    assert result is not None
    assert result.tool_name == "read_file"
    assert result.arguments == {"path": "src/main.py"}


def test_catches_json_decode_error_returns_none():
    assert _parser().parse("{not valid json!!!}") is None


def test_returns_none_when_name_missing():
    raw = json.dumps({"arguments": {"path": "x"}})
    assert _parser().parse(raw) is None


def test_returns_none_when_arguments_not_a_dict():
    raw = json.dumps({"name": "read_file", "arguments": "bad"})
    assert _parser().parse(raw) is None
