from navigator.llm import _payload


def test_cached_claude_cli_envelope_is_unwrapped() -> None:
    assert _payload({"result": '{"rules": [{"title": "cached"}]}'}) == {
        "rules": [{"title": "cached"}]
    }


def test_cached_fenced_json_is_unwrapped() -> None:
    assert _payload({"result": '```json\n{"rules": []}\n```'}) == {"rules": []}
