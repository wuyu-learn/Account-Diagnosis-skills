#!/usr/bin/env python3
"""Validate an LLM account plan and build deterministic business items."""

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


class SkeletonError(ValueError):
    """Raised when an account plan violates the deterministic contract."""


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SkeletonError(f"{path} must be an object")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SkeletonError(f"{path} must be a non-empty string")
    return value.strip()


def normalize_account_scenes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise SkeletonError("accountScenes must be a non-empty array")

    scenes: list[dict[str, Any]] = []
    previous_weight = 1.0
    for index, raw_scene in enumerate(value):
        scene = require_object(raw_scene, f"accountScenes[{index}]")
        unsupported = sorted(set(scene) - {"intent", "weight", "subQuery"})
        if unsupported:
            raise SkeletonError(
                f"accountScenes[{index}] has unsupported fields: "
                + ", ".join(unsupported)
            )

        intent = require_string(scene.get("intent"), f"accountScenes[{index}].intent")
        if intent not in ACCOUNT_INTENTS:
            raise SkeletonError(
                f"accountScenes[{index}].intent is unsupported: {intent}"
            )

        weight = scene.get("weight")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            raise SkeletonError(f"accountScenes[{index}].weight must be a number")
        if not 0 <= weight <= 1:
            raise SkeletonError(
                f"accountScenes[{index}].weight must be between 0 and 1"
            )
        if weight > previous_weight:
            raise SkeletonError("accountScenes must be sorted by weight descending")
        previous_weight = float(weight)

        scenes.append(
            {
                "intent": intent,
                "weight": weight,
                "subQuery": require_string(
                    scene.get("subQuery"), f"accountScenes[{index}].subQuery"
                ),
            }
        )
    return scenes


def normalize_params(card_id: str, value: Any, index: int) -> dict[str, str]:
    params = require_object(value, f"cardPlans[{index}].params")
    spec = CARD_SPECS[card_id]
    allowed_params = tuple(spec["allowedParams"])
    required_params = tuple(spec["requiredParams"])

    for key in params:
        if key in IDENTITY_KEYS:
            raise SkeletonError(
                f"cardPlans[{index}].params must not carry identity param '{key}'"
            )
        if key not in allowed_params:
            if allowed_params:
                raise SkeletonError(
                    f"cardPlans[{index}].params for {card_id} only allows "
                    f"{list(allowed_params)}, got '{key}'"
                )
            raise SkeletonError(
                f"cardPlans[{index}].params for {card_id} must be empty"
            )

    missing = [key for key in required_params if key not in params]
    if missing:
        raise SkeletonError(
            f"cardPlans[{index}].params for {card_id} is missing required "
            f"param(s): {', '.join(missing)}"
        )

    normalized: dict[str, str] = {}
    for key in allowed_params:
        if key not in params:
            continue
        normalized[key] = require_string(
            params[key], f"cardPlans[{index}].params.{key}"
        )

    if card_id == "ACC-15" and not is_valid_date_type(normalized["dateType"]):
        raise SkeletonError(
            f"cardPlans[{index}].params.dateType is unsupported: "
            f"{normalized['dateType']}"
        )
    return normalized


def build_result_skeleton(payload: Any) -> dict[str, Any]:
    root = require_object(payload, "input")
    allowed_root_keys = {
        "taskComplexity",
        "complexityReason",
        "primaryAccountIntent",
        "accountScenes",
        "cardPlans",
    }
    unsupported = sorted(set(root) - allowed_root_keys)
    if unsupported:
        raise SkeletonError("input has unsupported fields: " + ", ".join(unsupported))

    complexity = require_string(root.get("taskComplexity"), "taskComplexity")
    if complexity not in TASK_COMPLEXITIES:
        raise SkeletonError(f"taskComplexity is unsupported: {complexity}")

    complexity_reason = require_string(
        root.get("complexityReason"), "complexityReason"
    )
    primary_intent = require_string(
        root.get("primaryAccountIntent"), "primaryAccountIntent"
    )
    if primary_intent not in ACCOUNT_INTENTS:
        raise SkeletonError(
            f"primaryAccountIntent is unsupported: {primary_intent}"
        )

    scenes = normalize_account_scenes(root.get("accountScenes"))
    if primary_intent != scenes[0]["intent"]:
        raise SkeletonError(
            "primaryAccountIntent must equal the first accountScenes intent"
        )

    raw_card_plans = root.get("cardPlans")
    if not isinstance(raw_card_plans, list) or not raw_card_plans:
        raise SkeletonError("cardPlans must be a non-empty array")

    entries: list[tuple[int, int, dict[str, Any]]] = []
    seen_card_ids: set[str] = set()
    primary_is_watchlist = primary_intent == "watchlist_valuation"
    primary_is_test = primary_intent == "account_test"
    if primary_is_watchlist and complexity != "simple":
        raise SkeletonError("watchlist_valuation only supports simple tasks")

    for index, raw_plan in enumerate(raw_card_plans):
        plan = require_object(raw_plan, f"cardPlans[{index}]")
        extra = sorted(set(plan) - {"cardId", "params"})
        if extra:
            raise SkeletonError(
                f"cardPlans[{index}] has unsupported fields: " + ", ".join(extra)
            )

        card_id = require_string(plan.get("cardId"), f"cardPlans[{index}].cardId")
        if card_id not in CARD_SPECS:
            raise SkeletonError(f"cardPlans[{index}].cardId is unsupported: {card_id}")
        if card_id in seen_card_ids:
            raise SkeletonError(f"duplicate cardId: {card_id}")
        seen_card_ids.add(card_id)

        if not primary_is_test and is_watchlist_card(card_id) != primary_is_watchlist:
            raise SkeletonError(
                "account diagnosis cards and watchlist cards must not be mixed"
            )

        params = normalize_params(card_id, plan.get("params", {}), index)
        spec = CARD_SPECS[card_id]
        section_type = str(spec["sectionType"])
        item = {
            "section": {
                "type": section_type,
                "title": str(spec["title"]),
                "narrative": str(spec["narrative"]),
            },
            "card": {
                "cardId": card_id,
                "dataMode": "deferred",
                "data": params,
            },
        }
        entries.append((SECTION_ORDER[section_type], index, item))

    entries.sort(key=lambda entry: (entry[0], entry[1]))
    business_items = [entry[2] for entry in entries]
    business_types = {item["section"]["type"] for item in business_items}
    declared_intents = {scene["intent"] for scene in scenes}
    undeclared_types = sorted(business_types - declared_intents)
    if undeclared_types:
        raise SkeletonError(
            "planned cards must match declared accountScenes intents: "
            + ", ".join(undeclared_types)
        )
    if not primary_is_test and primary_intent not in business_types:
        raise SkeletonError(
            "primaryAccountIntent must match at least one planned card"
        )

    return {
        "taskComplexity": complexity,
        "complexityReason": complexity_reason,
        "primaryAccountIntent": primary_intent,
        "businessItems": business_items,
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
        description="Build deterministic account business items from an LLM plan."
    )
    parser.add_argument("--input", "-i", default="-", help="Input JSON path")
    parser.add_argument("--output", "-o", default="-", help="Output JSON path")
    args = parser.parse_args()

    try:
        with open_input(args.input) as source:
            payload = json.load(source)
        write_output(args.output, build_result_skeleton(payload))
    except (OSError, json.JSONDecodeError, SkeletonError) as error:
        print(f"build_result_skeleton: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
