from __future__ import annotations

import json
from types import SimpleNamespace

from navigator import llm


def test_cached_claude_cli_envelope_is_unwrapped() -> None:
    assert llm._payload({"result": '{"rules": [{"title": "cached"}]}'}) == {
        "rules": [{"title": "cached"}]
    }


def test_cached_fenced_json_is_unwrapped() -> None:
    assert llm._payload({"result": '```json\n{"rules": []}\n```'}) == {"rules": []}


def test_document_scoped_identity_reuses_a_safe_legacy_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "CACHE_ROOT", tmp_path / "cache")
    monkeypatch.setattr(llm, "LOG_ROOT", tmp_path / "logs")
    legacy = llm._cache_path("extract-v1", "fixture", "same-chunk")
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"result": '{"rules": [], "no_rule_reason": "legacy"}'}))
    monkeypatch.setattr(llm.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy cache should be used")))

    result = llm.complete(
        "fixture prompt",
        doc_id="D001",
        chunk_hash="same-chunk",
        prompt_version="extract-v1",
        model="fixture",
        cache_identity="D001|same-chunk",
    )

    assert result["no_rule_reason"] == "legacy"


def test_document_scoped_collision_bypasses_legacy_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "CACHE_ROOT", tmp_path / "cache")
    monkeypatch.setattr(llm, "LOG_ROOT", tmp_path / "logs")
    legacy = llm._cache_path("extract-v1", "fixture", "same-chunk")
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"result": '{"rules": [], "no_rule_reason": "wrong document"}'}))
    envelope = {"result": '{"rules": [], "no_rule_reason": "fresh document"}'}
    monkeypatch.setattr(
        llm.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(envelope), stderr=""),
    )

    result = llm.complete(
        "fixture prompt",
        doc_id="D046",
        chunk_hash="same-chunk",
        prompt_version="extract-v1",
        model="fixture",
        cache_identity="D046|same-chunk",
        allow_legacy_cache=False,
    )

    assert result["no_rule_reason"] == "fresh document"
    assert llm._cache_path("extract-v1", "fixture", "D046|same-chunk").exists()
