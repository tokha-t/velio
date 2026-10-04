from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .paths import CACHE_ROOT, LOG_ROOT


def _append_audit(record: dict[str, object]) -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    with (LOG_ROOT / "audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _payload(envelope: object) -> dict:
    content = envelope.get("result", envelope) if isinstance(envelope, dict) else envelope
    if isinstance(content, str):
        stripped = content.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(stripped)
    if not isinstance(content, dict):
        raise TypeError(f"LLM response must decode to an object, got {type(content).__name__}")
    return content


def _cache_path(prompt_version: str, model: str, identity: str) -> Path:
    key = hashlib.sha256(f"{prompt_version}|{model}|{identity}".encode()).hexdigest()
    return CACHE_ROOT / "llm" / f"{key}.json"


def complete(
    prompt: str,
    *,
    doc_id: str,
    chunk_hash: str,
    prompt_version: str,
    model: str | None = None,
    cache_identity: str | None = None,
    allow_legacy_cache: bool = True,
) -> dict:
    """Return a cached extraction, keeping distinct document prompts distinct.

    Older cache entries were keyed only by the normalized chunk text.  That is
    reusable for ordinary chunks, but not when two documents have identical
    text and different metadata (for example a bill page and its history).
    """
    backend = os.getenv("NAV_LLM_BACKEND", "claude_cli")
    model = model or os.getenv("NAV_MODEL", "claude-sonnet-5-5")
    identity = cache_identity or chunk_hash
    path = _cache_path(prompt_version, model, identity)
    if path.exists():
        return _payload(json.loads(path.read_text()))
    legacy_path = _cache_path(prompt_version, model, chunk_hash)
    if identity != chunk_hash and allow_legacy_cache and legacy_path.exists():
        return _payload(json.loads(legacy_path.read_text()))
    if backend == "claude_cli":
        command = ["claude", "-p", "--output-format", "json", "--model", model]
        process = subprocess.run(command, input=prompt, text=True, capture_output=True, check=False, timeout=240)
        if process.returncode:
            raise RuntimeError(process.stderr.strip() or process.stdout.strip())
        envelope = json.loads(process.stdout)
        content = envelope.get("result", envelope)
    elif backend == "anthropic":
        from anthropic import Anthropic
        response = Anthropic().messages.create(model=model, max_tokens=8192, temperature=0, messages=[{"role": "user", "content": prompt}])
        content = response.content[0].text
        envelope = {"result": content, "model": response.model, "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}}
    else:
        raise ValueError(f"Unsupported NAV_LLM_BACKEND={backend}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n")
    _append_audit({"event": "llm_call", "at": datetime.now(timezone.utc).isoformat(), "backend": backend, "doc_id": doc_id, "chunk_hash": chunk_hash, "cache_identity": identity, "model": model, "prompt_version": prompt_version, "response_hash": hashlib.sha256(str(content).encode()).hexdigest(), "cache_key": path.stem})
    return _payload(envelope)
