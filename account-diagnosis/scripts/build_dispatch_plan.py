#!/usr/bin/env python3
"""Validate account intent routing and build an internal module execution plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO


INTENT_TO_MODULE = {
    "account_overview": "references/account-asset-overview.md",
    "holding_structure": "references/account-holding-structure.md",
    "return_performance": "references/account-return-performance.md",
    "return_attribution": "references/account-return-attribution.md",
    "watchlist_valuation": "references/account-watchlist-valuation.md",
}

ALLOWED_ROUTER_KEYS = {
    "accountScenes",
    "primaryAccountIntent",
    "isMultiAccountIntent",
}

ALLOWED_ENTITY_KEYS = (
    "fund_names",
    "fund_codes",
    "manager_names",
    "company_names",
    "market_subjects",
    "strategy_names",
)


class DispatchError(ValueError):
    """Raised when the account routing result violates its contract."""


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DispatchError(f"{path} must be an object")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DispatchError(f"{path} must be a non-empty string")
    return value


def normalize_entities(value: Any) -> dict[str, list[Any]]:
    entities = require_object(value, "entities")
    normalized: dict[str, list[Any]] = {}
    for key in ALLOWED_ENTITY_KEYS:
        if key not in entities:
            continue
        entity_values = entities[key]
        if not isinstance(entity_values, list):
            raise DispatchError(f"entities.{key} must be an array")
        normalized[key] = [
            require_string(item, f"entities.{key}[{index}]")
            for index, item in enumerate(entity_values)
        ]
    return normalized


def build_dispatch_plan(payload: Any) -> dict[str, Any]:
    root = require_object(payload, "input")
    unexpected_root_keys = sorted(set(root) - {"accountIntentResult", "entities"})
    if unexpected_root_keys:
        raise DispatchError(
            "input has unsupported fields: " + ", ".join(unexpected_root_keys)
        )

    router = require_object(root.get("accountIntentResult"), "accountIntentResult")
    entities = normalize_entities(root.get("entities", {}))

    unexpected = sorted(set(router) - ALLOWED_ROUTER_KEYS)
    if unexpected:
        raise DispatchError(
            "accountIntentResult has unsupported fields: " + ", ".join(unexpected)
        )

    scenes = router.get("accountScenes")
    if not isinstance(scenes, list):
        raise DispatchError("accountIntentResult.accountScenes must be an array")

    primary = router.get("primaryAccountIntent")
    multi = router.get("isMultiAccountIntent")
    if not isinstance(multi, bool):
        raise DispatchError(
            "accountIntentResult.isMultiAccountIntent must be a boolean"
        )
    if multi != (len(scenes) >= 2):
        raise DispatchError(
            "isMultiAccountIntent must be true exactly when accountScenes has at least two records"
        )

    calls: list[dict[str, Any]] = []
    for index, raw_scene in enumerate(scenes):
        scene = require_object(raw_scene, f"accountScenes[{index}]")
        allowed_scene_keys = {"intent", "weight", "subQuery"}
        extra_scene_keys = sorted(set(scene) - allowed_scene_keys)
        if extra_scene_keys:
            raise DispatchError(
                f"accountScenes[{index}] has unsupported fields: "
                + ", ".join(extra_scene_keys)
            )

        intent = require_string(scene.get("intent"), f"accountScenes[{index}].intent")
        if intent not in INTENT_TO_MODULE:
            raise DispatchError(f"accountScenes[{index}] has unsupported intent: {intent}")

        weight = scene.get("weight")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            raise DispatchError(f"accountScenes[{index}].weight must be a number")
        if not 0 <= weight <= 1:
            raise DispatchError(f"accountScenes[{index}].weight must be between 0 and 1")

        sub_query = require_string(
            scene.get("subQuery"), f"accountScenes[{index}].subQuery"
        )
        calls.append(
            {
                "order": index,
                "module": INTENT_TO_MODULE[intent],
                "input": {
                    "intent": intent,
                    "subQuery": sub_query,
                    "entities": entities,
                },
            }
        )

    if not scenes:
        if primary is not None:
            raise DispatchError(
                "primaryAccountIntent must be null when accountScenes is empty"
            )
    else:
        first_intent = scenes[0].get("intent")
        if primary != first_intent:
            raise DispatchError(
                "primaryAccountIntent must equal the first accountScenes intent"
            )

    return {
        "calls": calls,
        "primaryAccountIntent": primary,
        "isMultiAccountIntent": multi,
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
        description="Build a deterministic account-module execution plan."
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
        write_output(args.output, build_dispatch_plan(payload))
    except (OSError, json.JSONDecodeError, DispatchError) as error:
        print(f"build_dispatch_plan: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
