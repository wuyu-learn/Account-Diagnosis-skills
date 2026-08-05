#!/usr/bin/env python3
"""Merge deterministic business items with LLM text into final v2.2 JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from account_contract import (
    ACCOUNT_INTENTS,
    CARD_SPECS,
    IDENTITY_KEYS,
    SECTION_ORDER,
    TASK_COMPLEXITIES,
    is_valid_date_type,
    is_watchlist_card,
)


SCENE = "问账户"
VERSION = "2.2"
DEFAULT_RISK_WARNING = "投资有风险，请结合自身情况审慎决策。"


class CompositionError(ValueError):
    """Raised when input violates the final account result contract."""


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CompositionError(f"{path} must be an object")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CompositionError(f"{path} must be a non-empty string")
    return value.strip()


def normalize_follow_up(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise CompositionError("followUp must be an array")

    result: list[str] = []
    for index, item in enumerate(value):
        follow_up = require_string(item, f"followUp[{index}]")
        if follow_up not in result:
            result.append(follow_up)
        if len(result) == 3:
            break
    return result


def normalize_text_section(value: Any, section_type: str) -> dict[str, str]:
    section = require_object(value, section_type)
    unsupported = sorted(set(section) - {"title", "narrative"})
    if unsupported:
        raise CompositionError(
            f"{section_type} has unsupported fields: " + ", ".join(unsupported)
        )
    return {
        "type": section_type,
        "title": require_string(section.get("title"), f"{section_type}.title"),
        "narrative": require_string(
            section.get("narrative"), f"{section_type}.narrative"
        ),
    }


def normalize_card(value: Any, index: int) -> dict[str, Any]:
    card = require_object(value, f"businessItems[{index}].card")
    unsupported = sorted(set(card) - {"cardId", "dataMode", "data"})
    if unsupported:
        raise CompositionError(
            f"businessItems[{index}].card has unsupported fields: "
            + ", ".join(unsupported)
        )

    card_id = require_string(
        card.get("cardId"), f"businessItems[{index}].card.cardId"
    )
    if card_id not in CARD_SPECS:
        raise CompositionError(
            f"businessItems[{index}].card.cardId is unsupported: {card_id}"
        )

    data_mode = require_string(
        card.get("dataMode"), f"businessItems[{index}].card.dataMode"
    )
    if data_mode != "deferred":
        raise CompositionError(
            f"businessItems[{index}].card.dataMode must be deferred"
        )

    data = require_object(card.get("data"), f"businessItems[{index}].card.data")
    spec = CARD_SPECS[card_id]
    allowed_params = tuple(spec["allowedParams"])
    required_params = tuple(spec["requiredParams"])

    for key in data:
        if key in IDENTITY_KEYS:
            raise CompositionError(
                f"businessItems[{index}].card.data must not carry identity param '{key}'"
            )
        if key not in allowed_params:
            if allowed_params:
                raise CompositionError(
                    f"businessItems[{index}].card.data for {card_id} only allows "
                    f"{list(allowed_params)}, got '{key}'"
                )
            raise CompositionError(
                f"businessItems[{index}].card.data for {card_id} must be empty"
            )

    missing = [key for key in required_params if key not in data]
    if missing:
        raise CompositionError(
            f"businessItems[{index}].card.data for {card_id} is missing required "
            f"param(s): {', '.join(missing)}"
        )

    normalized_data: dict[str, str] = {}
    for key in allowed_params:
        if key not in data:
            continue
        normalized_data[key] = require_string(
            data[key], f"businessItems[{index}].card.data.{key}"
        )

    if card_id == "ACC-15" and not is_valid_date_type(
        normalized_data["dateType"]
    ):
        raise CompositionError(
            f"businessItems[{index}].card.data.dateType is unsupported: "
            f"{normalized_data['dateType']}"
        )

    return {"cardId": card_id, "dataMode": data_mode, "data": normalized_data}


def normalize_business_item(
    value: Any, index: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    item = require_object(value, f"businessItems[{index}]")
    unsupported = sorted(set(item) - {"section", "card"})
    if unsupported:
        raise CompositionError(
            f"businessItems[{index}] has unsupported fields: "
            + ", ".join(unsupported)
        )
    if "section" not in item or "card" not in item:
        raise CompositionError(
            f"businessItems[{index}] must contain section and card"
        )

    card = normalize_card(item["card"], index)
    card_id = card["cardId"]
    spec = CARD_SPECS[card_id]

    section = require_object(item["section"], f"businessItems[{index}].section")
    extra_section_fields = sorted(set(section) - {"type", "title", "narrative"})
    if extra_section_fields:
        raise CompositionError(
            f"businessItems[{index}].section has unsupported fields: "
            + ", ".join(extra_section_fields)
        )

    section_type = require_string(
        section.get("type"), f"businessItems[{index}].section.type"
    )
    expected_type = str(spec["sectionType"])
    if section_type != expected_type:
        raise CompositionError(
            f"businessItems[{index}] card {card_id} requires section.type "
            f"{expected_type}, got {section_type}"
        )

    title = require_string(
        section.get("title"), f"businessItems[{index}].section.title"
    )
    narrative = require_string(
        section.get("narrative"), f"businessItems[{index}].section.narrative"
    )
    if title != spec["title"] or narrative != spec["narrative"]:
        raise CompositionError(
            f"businessItems[{index}] section text must match the fixed card contract"
        )

    normalized_section = {
        "type": section_type,
        "title": title,
        "narrative": narrative,
        "cardId": card_id,
    }
    return normalized_section, card


def compose_result(payload: Any) -> dict[str, Any]:
    root = require_object(payload, "input")
    allowed_root_keys = {
        "scene",
        "taskComplexity",
        "primaryAccountIntent",
        "businessItems",
        "summary",
        "conclusion",
        "followUp",
    }
    unsupported = sorted(set(root) - allowed_root_keys)
    if unsupported:
        raise CompositionError("input has unsupported fields: " + ", ".join(unsupported))

    scene = require_string(root.get("scene"), "scene")
    if scene != SCENE:
        raise CompositionError(f"scene must be {SCENE}")

    complexity = require_string(root.get("taskComplexity"), "taskComplexity")
    if complexity not in TASK_COMPLEXITIES:
        raise CompositionError(f"taskComplexity is unsupported: {complexity}")

    primary_intent = require_string(
        root.get("primaryAccountIntent"), "primaryAccountIntent"
    )
    if primary_intent not in ACCOUNT_INTENTS:
        raise CompositionError(
            f"primaryAccountIntent is unsupported: {primary_intent}"
        )
    if primary_intent == "watchlist_valuation" and complexity != "simple":
        raise CompositionError("watchlist_valuation only supports simple tasks")

    summary = normalize_text_section(root.get("summary"), "summary")
    if complexity == "simple":
        if "conclusion" in root:
            raise CompositionError("simple task must not include conclusion")
        conclusion = None
    else:
        if "conclusion" not in root:
            raise CompositionError("complex task requires conclusion")
        conclusion = normalize_text_section(root.get("conclusion"), "conclusion")

    raw_business_items = root.get("businessItems")
    if not isinstance(raw_business_items, list) or not raw_business_items:
        raise CompositionError("businessItems must be a non-empty array")

    business_sections: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    seen_card_ids: set[str] = set()
    previous_rank = -1
    primary_is_watchlist = primary_intent == "watchlist_valuation"
    primary_is_test = primary_intent == "account_test"

    for index, raw_item in enumerate(raw_business_items):
        section, card = normalize_business_item(raw_item, index)
        card_id = card["cardId"]
        if card_id in seen_card_ids:
            raise CompositionError(f"duplicate cardId: {card_id}")
        seen_card_ids.add(card_id)

        if not primary_is_test and is_watchlist_card(card_id) != primary_is_watchlist:
            raise CompositionError(
                "account diagnosis cards and watchlist cards must not be mixed"
            )

        rank = SECTION_ORDER[section["type"]]
        if rank < previous_rank:
            raise CompositionError(
                f"businessItems[{index}].section.type {section['type']} "
                "violates the fixed section order"
            )
        previous_rank = rank
        business_sections.append(section)
        cards.append(card)

    if not primary_is_test and primary_intent not in {section["type"] for section in business_sections}:
        raise CompositionError(
            "primaryAccountIntent must match at least one business section"
        )

    sections = [summary, *business_sections]
    if conclusion is not None:
        sections.append(conclusion)

    return {
        "version": VERSION,
        "meta": {"scene": SCENE, "intent": primary_intent},
        "sections": sections,
        "cards": cards,
        "risk_warning": DEFAULT_RISK_WARNING,
        "followUp": normalize_follow_up(root.get("followUp", [])),
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
        description="Compose a final v2.2 account-domain result JSON."
    )
    parser.add_argument("--input", "-i", default="-", help="Input JSON path")
    parser.add_argument("--output", "-o", default="-", help="Output JSON path")
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
