#!/usr/bin/env python3
"""Inject share-level identifiers (serialNo/uri) into deferred card data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from account_contract import CARD_SPECS, IDENTITY_KEYS


# Share-level cards: serialNo/uri locate a specific 份额 of a product.
# productId (ACC-19, product-level) is filled at plan time, not here.
SHARE_PARAM_CARDS = frozenset({"ACC-03", "ACC-05", "ACC-06", "ACC-08", "ACC-10"})
SHARE_PARAMS = ("serialNo", "uri")


class EnrichmentError(ValueError):
    """Raised when a share-binding payload violates the enrichment contract."""


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EnrichmentError(f"{path} must be an object")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnrichmentError(f"{path} must be a non-empty string")
    return value.strip()


def normalize_binding(value: Any, index: int) -> tuple[str, dict[str, str]]:
    binding = require_object(value, f"shareBindings[{index}]")
    unsupported = sorted(set(binding) - {"cardId", "serialNo", "uri"})
    if unsupported:
        raise EnrichmentError(
            f"shareBindings[{index}] has unsupported fields: " + ", ".join(unsupported)
        )

    card_id = require_string(binding.get("cardId"), f"shareBindings[{index}].cardId")
    if card_id not in SHARE_PARAM_CARDS:
        raise EnrichmentError(
            f"shareBindings[{index}].cardId must be a share-level card "
            f"({sorted(SHARE_PARAM_CARDS)}), got '{card_id}'"
        )

    normalized: dict[str, str] = {}
    for key in SHARE_PARAMS:
        normalized[key] = require_string(binding.get(key), f"shareBindings[{index}].{key}")
    return card_id, normalized


def enrich_share_identifiers(payload: Any) -> dict[str, Any]:
    root = require_object(payload, "input")
    allowed_root_keys = {"businessItems", "shareBindings"}
    unsupported = sorted(set(root) - allowed_root_keys)
    if unsupported:
        raise EnrichmentError("input has unsupported fields: " + ", ".join(unsupported))

    raw_business_items = root.get("businessItems")
    if not isinstance(raw_business_items, list) or not raw_business_items:
        raise EnrichmentError("businessItems must be a non-empty array")

    raw_bindings = root.get("shareBindings", [])
    if not isinstance(raw_bindings, list):
        raise EnrichmentError("shareBindings must be an array")

    bindings: dict[str, dict[str, str]] = {}
    for index, raw_binding in enumerate(raw_bindings):
        card_id, normalized = normalize_binding(raw_binding, index)
        if card_id in bindings:
            raise EnrichmentError(f"duplicate shareBinding for cardId: {card_id}")
        bindings[card_id] = normalized

    enriched_items: list[dict[str, Any]] = []
    matched: set[str] = set()
    for index, raw_item in enumerate(raw_business_items):
        item = require_object(raw_item, f"businessItems[{index}]")
        card = require_object(item.get("card"), f"businessItems[{index}].card")
        card_id = require_string(
            card.get("cardId"), f"businessItems[{index}].card.cardId"
        )

        if card_id in bindings:
            existing_data = card.get("data", {})
            if not isinstance(existing_data, dict):
                raise EnrichmentError(
                    f"businessItems[{index}].card.data must be an object"
                )
            for key in existing_data:
                if key in IDENTITY_KEYS:
                    raise EnrichmentError(
                        f"businessItems[{index}].card.data must not carry "
                        f"identity param '{key}'"
                    )
                if key not in SHARE_PARAMS:
                    raise EnrichmentError(
                        f"businessItems[{index}].card.data for {card_id} must only "
                        f"carry {list(SHARE_PARAMS)}, got '{key}'"
                    )
            enriched_card = dict(card)
            enriched_card["data"] = dict(bindings[card_id])
            enriched_item = dict(item)
            enriched_item["card"] = enriched_card
            enriched_items.append(enriched_item)
            matched.add(card_id)
        else:
            enriched_items.append(item)

    unmatched = sorted(set(bindings) - matched)
    if unmatched:
        raise EnrichmentError(
            "shareBindings reference absent businessItems: " + ", ".join(unmatched)
        )

    return {"businessItems": enriched_items}


def open_input(path: str) -> TextIO:
    if path == "-":
        return sys.stdin
    return Path(path).open("r", encoding="utf-8")


def write_output(path: str, result: dict[str, Any]) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if path == "-":
        sys.stdout.write(text)
    else:
        Path(path).write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inject share-level serialNo/uri into account deferred card data."
    )
    parser.add_argument("--input", "-i", default="-", help="Input JSON path")
    parser.add_argument("--output", "-o", default="-", help="Output JSON path")
    args = parser.parse_args()

    try:
        with open_input(args.input) as source:
            payload = json.load(source)
        write_output(args.output, enrich_share_identifiers(payload))
    except (OSError, json.JSONDecodeError, EnrichmentError) as error:
        print(f"enrich_share_identifiers: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
