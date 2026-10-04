from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz.fuzz import ratio

from .corpus import normalization_map, normalize


@dataclass(frozen=True)
class VerifiedQuote:
    text: str
    char_range: tuple[int, int]
    method: str
    score: float


def _raw_range(raw: str, normalized_start: int, normalized_end: int) -> tuple[int, int]:
    _, offsets = normalization_map(raw)
    return offsets[normalized_start], offsets[normalized_end - 1] + 1


def verify_quote(quote: str, raw: str, threshold: float = 95.0) -> VerifiedQuote | None:
    normalized_raw, _ = normalization_map(raw)
    normalized_quote = normalize(quote)
    start = normalized_raw.find(normalized_quote)
    if start >= 0:
        begin, end = _raw_range(raw, start, start + len(normalized_quote))
        return VerifiedQuote(raw[begin:end], (begin, end), "normalized_exact", 100.0)
    # Deterministically snap to same-length windows around uncommon quote tokens.
    length = len(normalized_quote)
    if length < 20 or not normalized_raw:
        return None
    candidates: set[int] = {0, max(0, len(normalized_raw) - length)}
    anchors = sorted((token for token in normalized_quote.split() if len(token) >= 7), key=lambda token: (-len(token), token))[:8]
    for token in anchors:
        cursor = 0
        while True:
            found = normalized_raw.find(token, cursor)
            if found < 0: break
            candidates.add(max(0, min(found, len(normalized_raw) - length)))
            candidates.add(max(0, min(found - normalized_quote.find(token), len(normalized_raw) - length)))
            cursor = found + 1
    best = max(((ratio(normalized_quote, normalized_raw[pos:pos + length]), pos) for pos in candidates), default=(0.0, 0))
    if best[0] < threshold:
        return None
    begin, end = _raw_range(raw, best[1], min(len(normalized_raw), best[1] + length))
    return VerifiedQuote(raw[begin:end], (begin, end), "rapidfuzz_snap", float(best[0]))
