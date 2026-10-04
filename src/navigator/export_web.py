"""Export pipeline artefacts for the static web application.

The browser only reads files under ``web/public/data``.  This module copies
the canonical JSON outputs without transforming their contents, and writes a
small deterministic manifest so the UI can distinguish unavailable pipeline
stages from an empty result.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .paths import BUILD_ROOT, ROOT


PUBLIC_DATA_ROOT = ROOT / "web" / "public" / "data"
SUBMISSION_ROOT = ROOT / "submission"
WEB_DATA_ROOT = ROOT / "web" / "data"
WEB_ARTIFACTS = (
    "addresses_resolved.json",
    "rules.json",
    "submission_rules.json",
    "changes.json",
    "changes_detail.json",
    "no_rule_findings.json",
    "validation.json",
    "lookups_2025-12-31.json",
    "lookups_2026-01-02.json",
    "lookups_2026-10-01.json",
    "lookups_2027-07-02.json",
)


def _copy(source: Path, destination: Path) -> bool:
    """Copy one existing JSON artefact and return whether it was available."""
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return True


def _first_existing(*paths: Path) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def run() -> dict[str, Any]:
    """Copy available pipeline outputs into ``web/public/data``.

    ``build/rules_internal.json`` takes precedence once Module A has finished;
    before then the UI receives the pilot records under the same ``rules.json``
    name.  Lookup outputs remain optional so the P4 mock interface can be
    built and demonstrated before P2 completes.
    """
    addresses = BUILD_ROOT / "addresses_resolved.json"
    if not addresses.exists():
        raise FileNotFoundError(f"Cannot export web data without {addresses}")

    PUBLIC_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    # A missing upstream artifact means that stage is unavailable, not that an
    # older browser payload should be retained.  Remove only files owned by
    # this exporter; source data and other public assets stay untouched.
    for filename in WEB_ARTIFACTS:
        (PUBLIC_DATA_ROOT / filename).unlink(missing_ok=True)

    exported: dict[str, str] = {}

    def copy_as(name: str, source: Path | None) -> None:
        if source and _copy(source, PUBLIC_DATA_ROOT / name):
            exported[name] = str(source.relative_to(ROOT))

    copy_as("addresses_resolved.json", addresses)
    copy_as(
        "rules.json",
        _first_existing(BUILD_ROOT / "rules_internal.json", BUILD_ROOT / "pilot_records.json"),
    )
    copy_as("submission_rules.json", SUBMISSION_ROOT / "rules.json")
    copy_as("changes.json", SUBMISSION_ROOT / "changes.json")
    copy_as("changes_detail.json", SUBMISSION_ROOT / "changes_detail.json")
    copy_as("no_rule_findings.json", SUBMISSION_ROOT / "no_rule_findings.json")
    copy_as("validation.json", _first_existing(WEB_DATA_ROOT / "validation.json", SUBMISSION_ROOT / "validation.json"))

    for as_of in ("2025-12-31", "2026-01-02", "2026-10-01", "2027-07-02"):
        source = _first_existing(
            SUBMISSION_ROOT / "lookups.json" if as_of == "2026-10-01" else BUILD_ROOT / f"lookups_{as_of}.json",
            BUILD_ROOT / f"lookups_{as_of}.json",
        )
        copy_as(f"lookups_{as_of}.json", source)

    manifest = {"files": dict(sorted(exported.items()))}
    (PUBLIC_DATA_ROOT / "data_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    print(json.dumps(run(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
