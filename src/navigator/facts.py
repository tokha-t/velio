"""Deterministic building-fact derivation for the supplied address data."""

from __future__ import annotations

import re
from typing import Any, Mapping


USE_CODE_RANGES: dict[str, tuple[int, int | None]] = {
    # Los Angeles, San Diego, Berkeley and New Jersey multi-family codes.
    "0500": (5, None),
    "0501": (5, None),
    "050C": (5, None),
    "050V": (5, None),
    "0551": (5, None),
    "14": (5, None),
    "15": (5, None),
    "16": (5, None),
    "7200": (5, None),
    "7700": (5, None),
    "7800": (5, None),
    "4C": (5, None),
    # San Francisco assessor codes.
    "A5": (5, 14),
    "F5": (5, 14),
    "FS5": (5, 14),
    "A15": (15, None),
    "TIC": (1, 4),
    # Boston and Cambridge assessor codes.
    "A/112": (7, 30),
    "A/118": (1, None),
    "A/120": (1, None),
    "A/125": (1, None),
    "111": (4, 8),
    "112": (9, None),
}

NJ_DESCRIPTION_UNITS = re.compile(r"(?<!\d)(\d+)\s*U(?:\b|-)", re.IGNORECASE)


def _positive_int(value: object) -> int | None:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def derive_facts(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return normalized facts without inferring facts absent from the dataset."""
    year_built = _positive_int(row.get("year_built"))
    column_units = _positive_int(row.get("units"))
    use_code = str(row.get("use_code", "")).strip()
    description = str(row.get("use_description", "")).strip()

    description_match = NJ_DESCRIPTION_UNITS.search(description) if use_code == "4C" else None
    description_units = int(description_match.group(1)) if description_match else None

    flags: list[str] = []
    description_upper = description.upper()
    if use_code == "A/125":
        flags.append("subsidized")
    if use_code == "A/118":
        flags.append("elderly")
    if "AFFORDABL" in description_upper:
        flags.append("affordable")

    # NJ descriptions can be more specific than the MOD-IV numeric column. A0227
    # is the documented example: column=2, description=93U, class=4C.
    if description_units is not None and (
        column_units is None
        or row.get("address_id") == "A0227"
        or description_units != column_units
    ):
        units = description_units
        units_range: list[int | None] = [units, units]
        units_source = "use_description"
        if column_units is not None and description_units != column_units:
            flags.append("units_column_conflicts_with_description")
    elif column_units is not None:
        units = column_units
        units_range = [units, units]
        units_source = "column"
    else:
        units = None
        lower, upper = USE_CODE_RANGES.get(use_code, (1, None))
        units_range = [lower, upper]
        units_source = "use_code" if use_code in USE_CODE_RANGES else "unknown"

    return {
        "year_built": year_built,
        "units": units,
        "units_range": units_range,
        "units_source": units_source,
        "flags": sorted(flags),
    }

