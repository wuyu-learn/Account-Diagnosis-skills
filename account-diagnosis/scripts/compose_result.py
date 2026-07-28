#!/usr/bin/env python3
"""Compose normalized result items into the final AI-advisor response JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO


CARD_ENDPOINTS = {
    "ACC-01": {"/v1/asset/agent/total"},
    "ACC-02": {"/v1/asset/agent/total"},
    "ACC-04": {"/v1/asset/agent/total"},
    "ACC-07": {"/v1/asset/agent/total"},
    "ACC-09": {"/v1/asset/agent/total"},
    "ACC-11": {"/v1/asset/agent/holding-detail"},
    "ACC-12": {"/v1/asset/agent/list/classify"},
    "ACC-13-A": {
        "/v1/asset/agent/analyze/profit/sum",
        "/v1/asset/agent/analyze/profit/yield",
    },
    "ACC-13-B": {"/v1/asset/agent/analyze/profit/yield"},
    "ACC-14": {"/v1/asset/agent/analyze/profit/calendar"},
    "ACC-15": {"/v1/asset/agent/analyze/attribution"},
    "ACC-19": {"/v1/asset/agent/share-detail"},
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
    data_mode = require_string(
        card.get("dataMode"), f"items[{index}].card.dataMode"
    )
    if data_mode not in {"inline", "deferred"}:
        raise CompositionError(
            f"items[{index}].card.dataMode must be inline or deferred"
        )

    data = require_object(card.get("data"), f"items[{index}].card.data")
    if data_mode == "deferred":
        request = require_object(
            data.get("request"), f"items[{index}].card.data.request"
        )
        allowed_request_keys = {"method", "path", "params"}
        unsupported_request_keys = sorted(set(request) - allowed_request_keys)
        if unsupported_request_keys:
            raise CompositionError(
                f"items[{index}].card.data.request has unsupported fields: "
                + ", ".join(unsupported_request_keys)
            )
        method = require_string(
            request.get("method"), f"items[{index}].card.data.request.method"
        )
        if method != "GET":
            raise CompositionError(
                f"items[{index}].card.data.request.method must be GET"
            )
        path = require_string(
            request.get("path"), f"items[{index}].card.data.request.path"
        )
        require_object(
            request.get("params"), f"items[{index}].card.data.request.params"
        )
        allowed_paths = CARD_ENDPOINTS.get(card_id)
        if allowed_paths is None:
            raise CompositionError(
                f"{card_id} has no confirmed deferred endpoint"
            )
        if path not in allowed_paths:
            raise CompositionError(
                f"{card_id} cannot use deferred endpoint: {path}"
            )

    return {"cardId": card_id, "dataMode": data_mode, "data": data}


def normalize_section(
    value: Any, index: int, card_id: str | None
) -> dict[str, Any]:
    section = dict(require_object(value, f"items[{index}].section"))
    require_string(section.get("type"), f"items[{index}].section.type")
    require_string(section.get("title"), f"items[{index}].section.title")

    if "content" in section:
        raise CompositionError(
            f"items[{index}].section.content is unsupported; use narrative"
        )
    if "narrative" in section:
        require_string(
            section["narrative"],
            f"items[{index}].section.narrative",
            allow_empty=True,
        )

    section_card_id = section.get("cardId")
    if section_card_id is not None:
        require_string(section_card_id, f"items[{index}].section.cardId")

    if card_id is not None:
        if section_card_id is not None and section_card_id != card_id:
            raise CompositionError(
                f"items[{index}] section.cardId does not match card.cardId"
            )
        section["cardId"] = card_id
    elif section_card_id is not None:
        raise CompositionError(
            f"items[{index}].section references a card that was not provided"
        )

    return section


def compose_result(payload: Any) -> dict[str, Any]:
    root = require_object(payload, "input")
    version = require_string(root.get("version"), "version")
    meta = require_object(root.get("meta"), "meta")
    items = root.get("items")
    if not isinstance(items, list):
        raise CompositionError("items must be an array")
    risk_warning = require_string(root.get("risk_warning"), "risk_warning")
    follow_up = normalize_follow_up(root.get("followUp", []))

    sections: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    seen_card_ids: set[str] = set()

    for index, raw_item in enumerate(items):
        item = require_object(raw_item, f"items[{index}]")
        raw_card = item.get("card")
        card = normalize_card(raw_card, index) if raw_card is not None else None
        card_id = card["cardId"] if card is not None else None
        sections.append(normalize_section(item.get("section"), index, card_id))

        if card is not None:
            if card_id in seen_card_ids:
                raise CompositionError(f"duplicate cardId: {card_id}")
            seen_card_ids.add(card_id)
            cards.append(card)

    return {
        "version": version,
        "meta": meta,
        "sections": sections,
        "cards": cards,
        "risk_warning": risk_warning,
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
        description="Compose normalized result items into a final response JSON."
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
