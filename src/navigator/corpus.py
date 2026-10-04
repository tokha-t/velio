from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import BUILD_ROOT, CORPUS_ROOT, RESEARCH_LINK_ONLY_ROOT

HEADER_RE = re.compile(r"\A(?:SOURCE: *(?P<source>[^\n]*)\n)?(?:RETRIEVED: *(?P<retrieved>[^\n]*)\n)?")
SECTION_RE = re.compile(r"(?m)^(?=(?:§|SECTION\b|SEC\.\b|Section\b|\d+[.)]\s|[IVX]+\.\s))", re.I)
DEFINITION_RE = re.compile(r"(?im)^.*\bdefinitions?\b.*$")


@dataclass(frozen=True)
class Document:
    doc_id: str
    jurisdictions: str
    url: str
    source_type: str
    retrieved_at: str
    text_path: Path
    text_sha256: str
    raw_text: str
    body: str
    source_tier: str
    corpus_text: bool


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    index: int
    text: str
    sha256: str


def normalize(text: str) -> str:
    table = str.maketrans({"\u00a0": " ", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-"})
    return re.sub(r"\s+", " ", text.translate(table)).strip()


def normalization_map(text: str) -> tuple[str, list[int]]:
    table = str.maketrans({"\u00a0": " ", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-"})
    chars: list[str] = []
    offsets: list[int] = []
    in_space = True
    for index, char in enumerate(text.translate(table)):
        if char.isspace():
            if not in_space:
                chars.append(" ")
                offsets.append(index)
            in_space = True
        else:
            chars.append(char)
            offsets.append(index)
            in_space = False
    if chars and chars[-1] == " ":
        chars.pop(); offsets.pop()
    return "".join(chars), offsets


def load_documents() -> list[Document]:
    rows = list(csv.DictReader((CORPUS_ROOT / "corpus_manifest.csv").open(encoding="utf-8-sig")))
    documents = []
    for row in rows:
        if not row.get("text_file"):
            continue
        path = CORPUS_ROOT / row["text_file"]
        raw = path.read_text(encoding="utf-8")
        match = HEADER_RE.match(raw)
        documents.append(Document(
            doc_id=row["doc_id"], jurisdictions=row["jurisdictions"], url=row["url"],
            source_type=row["source_type"], retrieved_at=row["retrieved_at"], text_path=path,
            text_sha256=hashlib.sha256(raw.encode()).hexdigest(), raw_text=raw,
            body=raw[match.end():] if match else raw,
            source_tier=_source_tier(row["source_type"]), corpus_text=True,
        ))
    return sorted(documents, key=lambda item: item.doc_id)


def _source_tier(source_type: str) -> str:
    normalized = source_type.lower()
    if normalized == "official":
        return "official"
    if "code publisher" in normalized:
        return "code_publisher"
    return "secondary"


def load_research_documents() -> list[Document]:
    """Load human-saved link-only pages without treating them as corpus text."""
    if not RESEARCH_LINK_ONLY_ROOT.exists():
        return []
    links_path = CORPUS_ROOT / "links_only.csv"
    links = {row["doc_id"]: row for row in csv.DictReader(links_path.open(encoding="utf-8-sig"))}
    documents: list[Document] = []
    for path in sorted(RESEARCH_LINK_ONLY_ROOT.glob("*.txt")):
        doc_id = path.stem
        source = links.get(doc_id)
        if source is None:
            base_match = re.match(r"(D\d+)", doc_id)
            source = links.get(base_match.group(1)) if base_match else None
        if source is None:
            raise ValueError(f"Research copy {path} has no matching row in links_only.csv")
        raw = path.read_text(encoding="utf-8")
        match = HEADER_RE.match(raw)
        header_url = match.group("source") if match else None
        header_retrieved = match.group("retrieved") if match else None
        documents.append(Document(
            doc_id=doc_id,
            jurisdictions=source["jurisdictions"],
            url=header_url or source["url"],
            source_type="link-only research",
            retrieved_at=header_retrieved or "",
            text_path=path,
            text_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            raw_text=raw,
            body=raw[match.end():] if match else raw,
            source_tier="link_only_research",
            corpus_text=False,
        ))
    return documents


def chunks(document: Document, max_chars: int = 24_000) -> list[Chunk]:
    pieces = [part.strip() for part in SECTION_RE.split(document.body) if part.strip()]
    if not pieces:
        pieces = [document.body]
    definitions = ""
    for index, part in enumerate(pieces):
        if DEFINITION_RE.search(part[:500]):
            definitions = part[:max_chars // 3]
            break
    packed: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) + 2 > max_chars:
            packed.append(current); current = ""
        if len(piece) > max_chars:
            if current: packed.append(current); current = ""
            packed.extend(piece[i:i + max_chars] for i in range(0, len(piece), max_chars))
        else:
            current = f"{current}\n\n{piece}".strip()
    if current: packed.append(current)
    result = []
    for index, text in enumerate(packed):
        if definitions and definitions not in text:
            text = f"DEFINITIONS CONTEXT:\n{definitions}\n\nSECTION TEXT:\n{text}"
        result.append(Chunk(document.doc_id, index, text, hashlib.sha256(text.encode()).hexdigest()))
    return result


def write_manifest(documents: list[Document] | None = None) -> list[dict[str, object]]:
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    selected = documents if documents is not None else load_documents()
    rows = [{"doc_id": doc.doc_id, "jurisdictions": doc.jurisdictions, "bytes": len(doc.raw_text.encode()), "chunks": len(chunks(doc)), "text_sha256": doc.text_sha256, "corpus_text": doc.corpus_text} for doc in selected]
    (BUILD_ROOT / "corpus_manifest.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    return rows
