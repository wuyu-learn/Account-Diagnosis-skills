#!/usr/bin/env python3
"""Normalize various upstream inputs into the standard Route Extract JSON.

The upstream Agent may send:
- a strict Route Extract JSON object;
- a JSON object missing fields or using variant entity shapes;
- a plain text string that is not JSON at all.

This script converts all of those into the canonical Route Extract shape so
that downstream Planner references and scripts can rely on a single contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO


SCENE_ACCOUNT = "问账户"
DEFAULT_PRIMARY_SCENE = SCENE_ACCOUNT
DEFAULT_CLARIFY = {"needed": False, "question": None}
DEFAULT_ORCHESTRATION = None

STANDARD_ENTITY_KEYS = (
    "fund_names",
    "fund_codes",
    "manager_names",
    "company_names",
    "market_subjects",
    "strategy_names",
)


class NormalizeInputError(ValueError):
    """Raised when the input cannot be normalized into a valid Route Extract."""


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize_entities(value: Any) -> dict[str, list[str]]:
    """Convert entity variants into the standard six string arrays."""
    entities: dict[str, list[str]] = {key: [] for key in STANDARD_ENTITY_KEYS}

    if not isinstance(value, dict):
        return entities

    # Standard keys are copied as-is when they are lists of strings.
    for key in STANDARD_ENTITY_KEYS:
        raw = value.get(key)
        if isinstance(raw, list):
            entities[key] = [str(item) for item in raw if _is_non_empty_string(item)]

    # Variant: funds as a list of {name, code} objects.
    funds = value.get("funds")
    if isinstance(funds, list):
        for item in funds:
            if isinstance(item, dict):
                name = item.get("name")
                code = item.get("code")
                if _is_non_empty_string(name) and name not in entities["fund_names"]:
                    entities["fund_names"].append(name)
                if _is_non_empty_string(code) and code not in entities["fund_codes"]:
                    entities["fund_codes"].append(code)
            elif _is_non_empty_string(item) and item not in entities["fund_names"]:
                entities["fund_names"].append(item)

    # Variant: single fund object.
    fund = value.get("fund")
    if isinstance(fund, dict):
        name = fund.get("name")
        code = fund.get("code")
        if _is_non_empty_string(name) and name not in entities["fund_names"]:
            entities["fund_names"].append(name)
        if _is_non_empty_string(code) and code not in entities["fund_codes"]:
            entities["fund_codes"].append(code)
    elif _is_non_empty_string(fund) and fund not in entities["fund_names"]:
        entities["fund_names"].append(fund)

    # Variant: singular arrays or strings for other entity types.
    _merge_string_entities(value, "manager", "manager_names", entities)
    _merge_string_entities(value, "managers", "manager_names", entities)
    _merge_string_entities(value, "company", "company_names", entities)
    _merge_string_entities(value, "companies", "company_names", entities)
    _merge_string_entities(value, "market_subject", "market_subjects", entities)
    _merge_string_entities(value, "market_subjects", "market_subjects", entities)
    _merge_string_entities(value, "strategy", "strategy_names", entities)
    _merge_string_entities(value, "strategies", "strategy_names", entities)

    return entities


def _merge_string_entities(
    source: dict[str, Any],
    source_key: str,
    target_key: str,
    target: dict[str, list[str]],
) -> None:
    raw = source.get(source_key)
    if _is_non_empty_string(raw):
        value = str(raw).strip()
        if value not in target[target_key]:
            target[target_key].append(value)
    elif isinstance(raw, list):
        for item in raw:
            if _is_non_empty_string(item):
                value = str(item).strip()
                if value not in target[target_key]:
                    target[target_key].append(value)


def _normalize_scene(value: Any, index: int) -> dict[str, Any]:
    if isinstance(value, str):
        return {
            "scene": SCENE_ACCOUNT,
            "weight": 1.0,
            "subQuery": value.strip(),
        }

    if not isinstance(value, dict):
        raise NormalizeInputError(f"scenes[{index}] must be a string or object")

    scene = str(value.get("scene", SCENE_ACCOUNT)).strip()
    if not scene:
        scene = SCENE_ACCOUNT

    weight = value.get("weight", 1.0)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        raise NormalizeInputError(f"scenes[{index}].weight must be a number")
    if not 0 <= weight <= 1:
        raise NormalizeInputError(f"scenes[{index}].weight must be between 0 and 1")

    sub_query = value.get("subQuery")
    if not _is_non_empty_string(sub_query):
        raise NormalizeInputError(f"scenes[{index}].subQuery must be a non-empty string")

    return {"scene": scene, "weight": float(weight), "subQuery": sub_query.strip()}


def _normalize_scenes(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []

    if isinstance(value, str):
        return [_normalize_scene(value, 0)]

    if isinstance(value, list):
        return [_normalize_scene(item, index) for index, item in enumerate(value)]

    raise NormalizeInputError("scenes must be a string, array or null")


def _derive_original_query(value: Any, scenes: list[dict[str, Any]]) -> str:
    if _is_non_empty_string(value):
        return str(value).strip()

    account_sub_queries = [
        scene["subQuery"] for scene in scenes if scene["scene"] == SCENE_ACCOUNT
    ]
    if account_sub_queries:
        return " ".join(account_sub_queries)

    if scenes:
        return " ".join(scene["subQuery"] for scene in scenes)

    raise NormalizeInputError("originalQuery cannot be derived: no valid scenes found")


def _normalize_clarify(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return DEFAULT_CLARIFY.copy()

    needed = value.get("needed", False)
    question = value.get("question")
    return {
        "needed": bool(needed),
        "question": question if _is_non_empty_string(question) else None,
    }


def normalize_input(raw: Any) -> dict[str, Any]:
    """Convert raw upstream input into the canonical Route Extract JSON."""
    if raw is None:
        raise NormalizeInputError("input is required")

    # Plain text: treat as the user's original question.
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise NormalizeInputError("input text is empty")

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, dict):
            raw = parsed
        else:
            return {
                "originalQuery": text,
                "scenes": [
                    {"scene": SCENE_ACCOUNT, "weight": 1.0, "subQuery": text}
                ],
                "entities": {key: [] for key in STANDARD_ENTITY_KEYS},
                "primaryScene": DEFAULT_PRIMARY_SCENE,
                "isMultiScene": False,
                "orchestration": DEFAULT_ORCHESTRATION,
                "clarify": DEFAULT_CLARIFY.copy(),
            }

    if not isinstance(raw, dict):
        raise NormalizeInputError("input must be a JSON object or a string")

    raw_original_query = raw.get("originalQuery")
    scenes = _normalize_scenes(raw.get("scenes"))

    # If scenes are missing but originalQuery is present, generate a default
    # account scene so downstream Planner still receives a standard input.
    if not scenes and _is_non_empty_string(raw_original_query):
        scenes = [_normalize_scene(raw_original_query, 0)]

    account_scenes = [scene for scene in scenes if scene["scene"] == SCENE_ACCOUNT]
    if not account_scenes:
        raise NormalizeInputError(f"at least one scene with scene='{SCENE_ACCOUNT}' is required")

    original_query = _derive_original_query(raw_original_query, account_scenes)
    entities = _normalize_entities(raw.get("entities"))

    primary_scene = raw.get("primaryScene", DEFAULT_PRIMARY_SCENE)
    if not _is_non_empty_string(primary_scene):
        primary_scene = DEFAULT_PRIMARY_SCENE

    is_multi_scene = raw.get("isMultiScene", False)
    if not isinstance(is_multi_scene, bool):
        is_multi_scene = bool(is_multi_scene)

    orchestration = raw.get("orchestration", DEFAULT_ORCHESTRATION)
    clarify = _normalize_clarify(raw.get("clarify"))

    return {
        "originalQuery": original_query,
        "scenes": scenes,
        "entities": entities,
        "primaryScene": primary_scene,
        "isMultiScene": is_multi_scene,
        "orchestration": orchestration,
        "clarify": clarify,
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
        description="Normalize upstream input into the standard Route Extract JSON."
    )
    parser.add_argument("--input", "-i", default="-", help="Input path")
    parser.add_argument("--output", "-o", default="-", help="Output path")
    args = parser.parse_args()

    try:
        with open_input(args.input) as source:
            raw_text = source.read()

        try:
            raw = json.loads(raw_text)
        except json.JSONDecodeError:
            raw = raw_text

        write_output(args.output, normalize_input(raw))
    except (OSError, json.JSONDecodeError, NormalizeInputError) as error:
        print(f"normalize_input: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
