from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pydantic import ValidationError

from .corpus import chunks, load_documents, load_research_documents, write_manifest
from .llm import complete
from .merge import run as merge_rules
from .models import ExtractionResponse
from .paths import BUILD_ROOT, ROOT
from .verify import verify_quote

PILOT_DOCS = ("D024", "D069", "D036", "D045", "D009")
PROMPT_PATH = ROOT / "prompts" / "extract_v1.md"


def _prompt(document, chunk_text: str) -> tuple[str, str]:
    template = PROMPT_PATH.read_text()
    version = re.search(r"PROMPT_VERSION: *([^\n]+)", template).group(1).strip()
    metadata = json.dumps({"doc_id": document.doc_id, "jurisdictions": document.jurisdictions, "url": document.url, "source_type": document.source_type}, sort_keys=True)
    return template.replace("{metadata}", metadata).replace("{chunk}", chunk_text), version


def _extract_chunk(document, chunk) -> list[dict]:
    records = []
    prompt, version = _prompt(document, chunk.text)
    payload = complete(prompt, doc_id=document.doc_id, chunk_hash=chunk.sha256, prompt_version=version)
    try:
        parsed = ExtractionResponse.model_validate(payload)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid extraction for {document.doc_id} chunk {chunk.index}: {exc}") from exc
    for rule in parsed.rules:
        verified = verify_quote(rule.quoted_span, document.raw_text)
        if verified is None:
            # §7.8 requires one copy-verbatim retry before a record is dropped.
            retry = prompt + "\n\nRETRY: The previous quote was not found. Return the same records but copy each quoted_span exactly from SECTION TEXT."
            retry_hash = hashlib.sha256((chunk.sha256 + "|quote-retry").encode()).hexdigest()
            retried = ExtractionResponse.model_validate(complete(retry, doc_id=document.doc_id, chunk_hash=retry_hash, prompt_version=version + "-quote-retry"))
            matching = [item for item in retried.rules if item.category == rule.category and item.citation == rule.citation]
            if matching:
                rule = matching[0]
                verified = verify_quote(rule.quoted_span, document.raw_text)
        if verified is None:
            continue
        record = rule.model_dump(mode="json")
        record.update({
            "source_doc_id": document.doc_id,
            "source_url": document.url,
            "retrieved_at": document.retrieved_at,
            "quote_verified": True,
            "quote_char_range": list(verified.char_range),
            "quote_match_method": verified.method,
            "quoted_span": verified.text,
            "source_tier": document.source_tier,
            "corpus_text": document.corpus_text,
        })
        records.append(record)
    return records


def _extract_job(document, chunk) -> tuple[list[dict], dict | None]:
    """Run one (document, chunk) extraction job with one retry and no fail-fast."""
    error: Exception | None = None
    for _attempt in range(2):
        try:
            return _extract_chunk(document, chunk), None
        except Exception as exc:  # A failed chunk must not stop other documents.
            error = exc
    return [], {
        "doc_id": document.doc_id,
        "chunk_index": chunk.index,
        "chunk_hash": chunk.sha256,
        "error": f"{type(error).__name__}: {error}",
    }


def _write_errors(errors: list[dict]) -> None:
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    ordered = sorted(errors, key=lambda item: (item["doc_id"], item["chunk_index"], item["chunk_hash"]))
    (BUILD_ROOT / "extract_errors.json").write_text(json.dumps({"errors": ordered}, indent=2, sort_keys=True) + "\n")


def _selected_documents(pilot: bool) -> list:
    documents = sorted(load_documents() + load_research_documents(), key=lambda item: item.doc_id)
    return [doc for doc in documents if not pilot or doc.doc_id in PILOT_DOCS]


def run(*, pilot: bool = False, smoke: bool = False) -> None:
    all_documents = sorted(load_documents() + load_research_documents(), key=lambda item: item.doc_id)
    manifest = write_manifest(all_documents)
    print(f"Loaded {sum(doc.corpus_text for doc in all_documents)} corpus text documents and {sum(not doc.corpus_text for doc in all_documents)} research copies")
    for row in manifest:
        print(f"{row['doc_id']}\t{row['bytes']} bytes\t{row['chunks']} chunks\t{row['text_sha256']}")
    if smoke:
        result = complete('Return exactly this JSON object and nothing else: {"rules": [], "no_rule_reason": "smoke ok"}', doc_id="SMOKE", chunk_hash=hashlib.sha256(b"smoke-v1").hexdigest(), prompt_version="smoke-v1")
        print(json.dumps(result, sort_keys=True))
        return
    selected = [doc for doc in all_documents if not pilot or doc.doc_id in PILOT_DOCS]
    jobs = [(document, chunk) for document in selected for chunk in chunks(document)]
    records: list[dict] = []
    errors: list[dict] = []
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="extract") as executor:
        futures = {executor.submit(_extract_job, document, chunk): (document, chunk) for document, chunk in jobs}
        for future in as_completed(futures):
            document, chunk = futures[future]
            try:
                job_records, error = future.result()
            except Exception as exc:  # Defensive: worker failures are still reported deterministically.
                job_records, error = [], {
                    "doc_id": document.doc_id,
                    "chunk_index": chunk.index,
                    "chunk_hash": chunk.sha256,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            records.extend(job_records)
            if error:
                errors.append(error)
    _write_errors(errors)
    records.sort(key=lambda item: (item["jurisdiction"], item["category"], item["citation"], item["source_doc_id"]))
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    output = BUILD_ROOT / ("pilot_records.json" if pilot else "extracted_records.json")
    output.write_text(json.dumps({"rules": records}, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"rules": records}, indent=2, sort_keys=True))
    if not pilot:
        merge_rules()
