#!/usr/bin/env python3
"""Compose normalized result items into an account-domain result JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO


SCENE = "问账户"

ACCOUNT_INTENTS = {
    "account_overview",
    "holding_structure",
    "return_performance",
    "return_attribution",
    "watchlist_valuation",
}

SECTION_ORDER = {
    "summary": 0,
    "account_overview": 1,
    "holding_structure": 2,
    "return_performance": 3,
    "return_attribution": 4,
    "watchlist_valuation": 5,
    "conclusion": 6,
}

CARD_TO_SECTION = {
    "ACC-01": "account_overview",
    "ACC-02": "account_overview",
    "ACC-03": "account_overview",
    "ACC-04": "account_overview",
    "ACC-05": "account_overview",
    "ACC-06": "account_overview",
    "ACC-07": "account_overview",
    "ACC-08": "account_overview",
    "ACC-09": "account_overview",
    "ACC-10": "account_overview",
    "ACC-11": "holding_structure",
    "ACC-12": "holding_structure",
    "ACC-13-A": "return_performance",
    "ACC-13-B": "return_performance",
    "ACC-14": "return_performance",
    "ACC-15": "return_attribution",
    "ACC-18": "watchlist_valuation",
    "ACC-19": "account_overview",
}


class CompositionError(ValueError):
    """Raised when input violates the result contract."""


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CompositionError(f"{path} must be an object")
    return value


def require_string(value: Any, path: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise CompositionError(f"{path} must be a string")
    if not allow_empty and not value.strip():
        raise CompositionError(f"{path} must not be empty")
    return value


def normalize_follow_up(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise CompositionError("followUp must be an array")

    result: list[str] = []
    for index, item in enumerate(value):
        text = require_string(item, f"followUp[{index}]").strip()
        if text not in result:
            result.append(text)
        if len(result) == 3:
            break
    return result


def normalize_card(value: Any, index: int) -> dict[str, Any]:
    card = require_object(value, f"items[{index}].card")
    allowed = {"cardId", "dataMode", "data"}
    unsupported = sorted(set(card) - allowed)
    if unsupported:
        raise CompositionError(
            f"items[{index}].card has unsupported fields: {', '.join(unsupported)}"
        )

    card_id = require_string(card.get("cardId"), f"items[{index}].card.cardId")
    if card_id not in CARD_TO_SECTION:
        raise CompositionError(
            f"items[{index}].card.cardId is unsupported: {card_id}"
        )

    data_mode = require_string(
        card.get("dataMode"), f"items[{index}].card.dataMode"
    )
    if data_mode != "deferred":
        raise CompositionError(
            f"items[{index}].card.dataMode must be deferred"
        )

    data = require_object(card.get("data"), f"items[{index}].card.data")
    if data:
        raise CompositionError(
            f"items[{index}].card.data must be empty; "
            "fetching is handled by the frontend component"
        )

    return {"cardId": card_id, "dataMode": data_mode, "data": data}


def normalize_section(
    value: Any, index: int, card_id: str | None
) -> dict[str, Any]:
    section = dict(require_object(value, f"items[{index}].section"))
    allowed = {"type", "title", "narrative", "cardId"}
    unsupported = sorted(set(section) - allowed)
    if unsupported:
        raise CompositionError(
            f"items[{index}].section has unsupported fields: "
            + ", ".join(unsupported)
        )

    section_type = require_string(
        section.get("type"), f"items[{index}].section.type"
    )
    if section_type not in SECTION_ORDER:
        raise CompositionError(
            f"items[{index}].section.type is unsupported: {section_type}"
        )
    require_string(section.get("title"), f"items[{index}].section.title")
    require_string(
        section.get("narrative"),
        f"items[{index}].section.narrative",
    )

    section_card_id = section.get("cardId")
    if section_card_id is not None:
        require_string(section_card_id, f"items[{index}].section.cardId")

    if card_id is not None:
        expected_section_type = CARD_TO_SECTION[card_id]
        if section_type != expected_section_type:
            raise CompositionError(
                f"items[{index}] card {card_id} requires section.type "
                f"{expected_section_type}, got {section_type}"
            )
        if section_card_id is not None and section_card_id != card_id:
            raise CompositionError(
                f"items[{index}] section.cardId does not match card.cardId"
            )
        section["cardId"] = card_id
    elif section_card_id is not None:
        raise CompositionError(
            f"items[{index}].section references a card that was not provided"
        )

    if section_type in {"summary", "conclusion"} and card_id is not None:
        raise CompositionError(
            f"items[{index}].section.type {section_type} must not have a card"
        )
    if section_type in ACCOUNT_INTENTS and card_id is None:
        raise CompositionError(
            f"items[{index}].section.type {section_type} must have a card"
        )

    return section


def compose_result(payload: Any) -> dict[str, Any]:
    root = require_object(payload, "input")
    allowed_root_keys = {
        "scene",
        "primaryAccountIntent",
        "items",
        "followUp",
    }
    unsupported_root_keys = sorted(set(root) - allowed_root_keys)
    if unsupported_root_keys:
        raise CompositionError(
            "input has unsupported fields: " + ", ".join(unsupported_root_keys)
        )

    scene = require_string(root.get("scene"), "scene")
    if scene != SCENE:
        raise CompositionError(f"scene must be {SCENE}")
    intent = require_string(
        root.get("primaryAccountIntent"), "primaryAccountIntent"
    )
    if intent not in ACCOUNT_INTENTS:
        raise CompositionError(
            f"primaryAccountIntent is unsupported: {intent}"
        )

    items = root.get("items")
    if not isinstance(items, list):
        raise CompositionError("items must be an array")
    if len(items) < 3:
        raise CompositionError(
            "items must contain summary, at least one business section, and conclusion"
        )

    follow_up = normalize_follow_up(root.get("followUp", []))

    sections: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    seen_card_ids: set[str] = set()
    section_types: list[str] = []

    for index, raw_item in enumerate(items):
        item = require_object(raw_item, f"items[{index}]")
        unsupported_item_keys = sorted(set(item) - {"section", "card"})
        if unsupported_item_keys:
            raise CompositionError(
                f"items[{index}] has unsupported fields: "
                + ", ".join(unsupported_item_keys)
            )

        raw_card = item.get("card")
        card = normalize_card(raw_card, index) if raw_card is not None else None
        card_id = card["cardId"] if card is not None else None
        section = normalize_section(item.get("section"), index, card_id)
        sections.append(section)
        section_types.append(section["type"])

        if card is not None:
            if card_id in seen_card_ids:
                raise CompositionError(f"duplicate cardId: {card_id}")
            seen_card_ids.add(card_id)
            cards.append(card)

    if section_types[0] != "summary":
        raise CompositionError("the first section must be summary")
    if section_types[-1] != "conclusion":
        raise CompositionError("the last section must be conclusion")
    if section_types.count("summary") != 1:
        raise CompositionError("exactly one summary section is required")
    if section_types.count("conclusion") != 1:
        raise CompositionError("exactly one conclusion section is required")

    previous_rank = -1
    for index, section_type in enumerate(section_types):
        rank = SECTION_ORDER[section_type]
        if rank < previous_rank:
            raise CompositionError(
                f"items[{index}].section.type {section_type} violates the fixed section order"
            )
        previous_rank = rank

    business_types = set(section_types[1:-1])
    if intent not in business_types:
        raise CompositionError(
            "primaryAccountIntent must match at least one business section"
        )

    return {
        "scene": SCENE,
        "primaryAccountIntent": intent,
        "sections": sections,
        "cards": cards,
        "followUp": follow_up,
    }


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
        description="Compose normalized items into an account-domain result JSON."
    )
    parser.add_argument(
        "--input", "-i", default="-", help="Input JSON path; use - for stdin"
    )
    parser.add_argument(
        "--output", "-o", default="-", help="Output JSON path; use - for stdout"
    )
    args = parser.parse_args()

    try:
        with open_input(args.input) as source:
            payload = json.load(source)
        write_output(args.output, compose_result(payload))
    except (OSError, json.JSONDecodeError, CompositionError) as error:
        print(f"compose_result: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
