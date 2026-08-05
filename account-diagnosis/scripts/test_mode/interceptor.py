#!/usr/bin/env python3
"""Detect the card-test directive and emit the test-mode routing signal.

Deterministic, no LLM, no MCP. Run after normalize_input. The interceptor only
decides whether the input should be routed to references/card-test-mode.md.
Whether the agent chooses full-card or single-card test mode is left to the
agent after reading that reference.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, TextIO

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE.parents[1]))

from account_contract import CARD_SPECS  # noqa: E402

TEST_INTENT = "account_test"
TEST_PREFIX = "问账户："
TEST_KEYWORD = "全部卡片测试"
CARD_ID_RE = re.compile(r"ACC-\d{2}(?:-[A-Z])?")

# Intents covered by the full-card test plan, ordered for deterministic output.
_COVERED_INTENTS = (
    "account_test",
    "account_overview",
    "holding_structure",
    "return_performance",
    "return_attribution",
    "watchlist_valuation",
)


def _intent_for_card(card_id: str) -> str:
    """Return the real business intent that a test card belongs to."""
    return str(CARD_SPECS[card_id]["sectionType"])


def _collect_unique_intents(card_ids: list[str]) -> list[str]:
    """Collect unique real business intents from requested cards, preserving order."""
    seen: set[str] = set()
    intents: list[str] = []
    for cid in card_ids:
        intent = _intent_for_card(cid)
        if intent not in seen:
            seen.add(intent)
            intents.append(intent)
    return intents


def _collect_texts(route_extract: Any) -> list[str]:
    """Collect originalQuery and all subQueries from the route extract."""
    if not isinstance(route_extract, dict):
        return []
    candidates: list[str] = []
    original_query = route_extract.get("originalQuery")
    if isinstance(original_query, str):
        candidates.append(original_query)
    scenes = route_extract.get("scenes")
    if isinstance(scenes, list):
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            sub_query = scene.get("subQuery")
            if isinstance(sub_query, str):
                candidates.append(sub_query)
    return candidates


def _is_test_format(text: str) -> bool:
    """测试模式入口的唯一判定：是否以'问账户：'开头。"""
    return text.startswith(TEST_PREFIX)


def is_test_mode(route_extract: Any) -> bool:
    """True when any input text starts with the account-test prefix.

    The interceptor intentionally does NOT decide single-card vs full-card;
    that is left to the agent after reading references/card-test-mode.md.
    """
    return any(_is_test_format(text) for text in _collect_texts(route_extract))


def parse_single_card_test(route_extract: Any) -> list[str] | None:
    """Extract valid ACC-XX card IDs after the account-test prefix.

    Does not require the word '测试'; any card id after '问账户：' is accepted.
    Returns None when no valid single-card pattern is found.
    """
    texts = _collect_texts(route_extract)
    if not texts:
        return None

    for text in texts:
        if not _is_test_format(text):
            continue
        body = text[len(TEST_PREFIX):]
        card_ids = CARD_ID_RE.findall(body)
        if not card_ids:
            continue
        seen: set[str] = set()
        unique: list[str] = []
        for cid in card_ids:
            if cid not in seen:
                seen.add(cid)
                unique.append(cid)
        if all(cid in CARD_SPECS for cid in unique):
            return unique

    return None


def is_full_test_keyword(route_extract: Any) -> bool:
    """Helper for the agent: does the input contain the explicit full-test keyword?"""
    texts = _collect_texts(route_extract)
    return any(_is_test_format(text) and TEST_KEYWORD in text for text in texts)


def detect_test_mode(route_extract: Any) -> dict[str, Any]:
    """Agent-facing entry point: only decides whether to route to card-test-mode.md."""
    if is_test_mode(route_extract):
        return {"testMode": True}
    return {"testMode": False}


def build_test_plan(card_ids: list[str] | None = None) -> dict[str, Any]:
    """Return the fixed account plan for test mode.

    Args:
        card_ids: If None, full-card test mode (all 18 cards).  Otherwise
            single-card test mode with only the specified cards.
    """
    if card_ids is None:
        return _build_full_test_plan()
    return _build_single_card_plan(card_ids)


def _build_full_test_plan() -> dict[str, Any]:
    card_ids = [
        "ACC-01",
        "ACC-02",
        "ACC-03",
        "ACC-04",
        "ACC-05",
        "ACC-06",
        "ACC-07",
        "ACC-08",
        "ACC-09",
        "ACC-10",
        "ACC-11",
        "ACC-12",
        "ACC-13-A",
        "ACC-13-B",
        "ACC-14",
        "ACC-15",
        "ACC-18",
        "ACC-19",
    ]
    return {
        "taskComplexity": "simple",
        "complexityReason": "卡片测试：全量输出全部账户卡片",
        "primaryAccountIntent": TEST_INTENT,
        "accountScenes": [
            {"intent": intent, "weight": 1.0 - index * 0.1, "subQuery": TEST_KEYWORD}
            for index, intent in enumerate(_COVERED_INTENTS)
        ],
        "cardPlans": _card_plans_for_ids(card_ids),
    }


def _build_single_card_plan(card_ids: list[str]) -> dict[str, Any]:
    keyword = ", ".join(card_ids) + "测试"

    # Collect unique real business intents from the requested cards, preserving order.
    real_intents = _collect_unique_intents(card_ids)

    account_scenes = [
        {"intent": TEST_INTENT, "weight": 1.0, "subQuery": keyword},
    ]
    weight = 0.9
    for intent in real_intents:
        account_scenes.append(
            {"intent": intent, "weight": weight, "subQuery": keyword}
        )
        weight -= 0.1

    return {
        "taskComplexity": "simple",
        "complexityReason": f"卡片测试：单卡测试 {keyword}",
        "primaryAccountIntent": TEST_INTENT,
        "accountScenes": account_scenes,
        "cardPlans": _card_plans_for_ids(card_ids),
    }


def _card_plans_for_ids(card_ids: list[str]) -> list[dict[str, Any]]:
    card_plans: list[dict[str, Any]] = []
    for cid in card_ids:
        params: dict[str, str] = {}
        if cid == "ACC-15":
            params["dateType"] = "N"
        card_plans.append({"cardId": cid, "params": params})
    return card_plans


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
        description="Detect the account card-test directive and emit the routing signal."
    )
    parser.add_argument("--input", "-i", default="-", help="Input Route Extract JSON path")
    parser.add_argument("--output", "-o", default="-", help="Output JSON path")
    args = parser.parse_args()

    try:
        with open_input(args.input) as source:
            route_extract = json.load(source)

        result = detect_test_mode(route_extract)
        write_output(args.output, result)
    except (OSError, json.JSONDecodeError) as error:
        print(f"interceptor: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
