#!/usr/bin/env python3
"""Inject locator identifiers into test-mode share cards from queryHoldingDetail.

Reads ``queryHoldingDetail``(type=1) and injects ONLY locator identifiers (never
analysis data) into share-level cards (ACC-03/05/06/08/10). The holding response is
product-level: ``categoryList[].itemList[]`` each carry ``fundId``/``serialNo``/``uri``,
so a single MCP covers both 大类 membership and the identifiers — no queryShareDetail
needed (which avoids the 份额-level response being truncated in the LLM context).

Injection (ACC-03/05/06/08/10): a 产品项 picked from the card's 大类 (``categoryCode``)
in ``queryHoldingDetail.categoryList[].itemList[]``, written to card.data as
``productId``/``balanceSerialNo``/``uri`` (MCP ``serialNo`` → ``balanceSerialNo``; the
产品项's ``fundId`` → ``productId``). Prefers a 产品项 with all three fields present;
falls back to any 产品项 in the 大类 (missing fields stay empty).

ACC-19: one ``productId`` (single fundId string). Prefers a multi-channel fundId (same
``fundId`` with ≥2 distinct ``serialNo`` across the holding items — i.e. the fundId
repeats in holdingDetail with different serialNos); falls back to any fundId; keeps
the card empty if there are no products.

Field-name assumptions are constants at the top (实测 schema; 联调改这里).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, TextIO

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE.parents[1]))

from test_contract import SHARE_PRODUCT_TYPES, is_share_card  # noqa: E402


# Field names of the queryHoldingDetail response (实测 schema; 联调改这里).
HOLDING_CATEGORIES = "categoryList"   # queryHoldingDetail 顶层分类数组
CATEGORY_CODE = "categoryCode"        # 分类编码 (大类标识)
CATEGORY_ITEMS = "itemList"           # 分类下的产品列表 (每项带 fundId/serialNo/uri)
FUND_ID = "fundId"                    # 产品代码
SERIAL_NO = "serialNo"                # MCP 响应字段 (读端)
URI = "uri"
BALANCE_SERIAL_NO = "balanceSerialNo"  # 卡片 data 输出字段名 (写端, MCP serialNo 值用此名写入)
PRODUCT_ID = "productId"               # 卡片 data 输出字段: 产品代码 (值取自产品项 fundId)


class EnrichTestError(ValueError):
    """Raised when a test-mode enrichment payload violates the contract."""


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EnrichTestError(f"{path} must be an object")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnrichTestError(f"{path} must be a non-empty string")
    return value.strip()


def _record_list(value: Any, path: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise EnrichTestError(f"{path} must be an array")
    return [require_object(item, f"{path}[{i}]") for i, item in enumerate(value)]


def _extract_items(value: Any, list_key: str, path: str) -> list[dict[str, Any]]:
    """Accept a raw MCP response, its ``body`` wrapper, or the list itself.

    Real MCP responses wrap the payload under ``body`` (e.g. ``{body: {categoryList: [...]}}``);
    when ``list_key`` is not at the top level, fall back to ``body.<list_key>``.
    """
    if isinstance(value, list):
        return _record_list(value, path)
    if isinstance(value, dict):
        items = value.get(list_key)
        if items is None and isinstance(value.get("body"), dict):
            items = value["body"].get(list_key)
        return _record_list(items or [], f"{path}.{list_key}")
    raise EnrichTestError(f"{path} must be an object or array")


def _category_to_items(holding_response: Any) -> dict[str, list[dict[str, Any]]]:
    """categoryCode -> list of 产品项, parsed from queryHoldingDetail.categoryList.

    每个产品项保留完整字段 (含 fundId/serialNo/uri), 供份额级卡片挑选.
    """
    categories = _extract_items(holding_response, HOLDING_CATEGORIES, "holdingDetail")
    mapping: dict[str, list[dict[str, Any]]] = {}
    for index, category in enumerate(categories):
        code = category.get(CATEGORY_CODE)
        if not (isinstance(code, str) and code.strip()):
            continue
        items = _record_list(
            category.get(CATEGORY_ITEMS) or [],
            f"holdingDetail[{index}].{CATEGORY_ITEMS}",
        )
        mapping.setdefault(code.strip(), []).extend(items)
    return mapping


def _pick_item(
    category_items: list[dict[str, Any]], rng: random.Random
) -> dict[str, Any] | None:
    """在该大类的产品项里挑一个。

    优先挑 fundId+serialNo+uri 三字段齐全的产品项, 让 productId/balanceSerialNo/uri
    都能填且同源; 该大类没有三字段齐全的, 再随机挑一项 (缺的字段注入时不填).
    大类无任何产品项时返回 None.
    """
    if not category_items:
        return None
    full = [
        item
        for item in category_items
        if isinstance(item.get(FUND_ID), str) and item[FUND_ID].strip()
        and isinstance(item.get(SERIAL_NO), str) and item[SERIAL_NO].strip()
        and isinstance(item.get(URI), str) and item[URI].strip()
    ]
    return rng.choice(full if full else category_items)


def _pick_fund_id(all_items: list[dict[str, Any]], rng: random.Random) -> str | None:
    """从所有产品项挑一个 fundId 作 ACC-19 的 productId。

    优先挑多渠道 fundId (同 fundId 下 distinct serialNo ≥ 2); 没有则任一 fundId;
    完全无产品返回 None。判定口径与多渠道一致, 数据源是 holdingDetail 产品项
    (同 fundId 在 holdingDetail 重复出现且 serialNo 不同 = 多渠道)。
    """
    serials_by_fund: dict[str, set[str]] = {}
    for item in all_items:
        fund_id = item.get(FUND_ID)
        serial_no = item.get(SERIAL_NO)
        if isinstance(fund_id, str) and fund_id.strip() and isinstance(serial_no, str) and serial_no.strip():
            serials_by_fund.setdefault(fund_id.strip(), set()).add(serial_no.strip())
    multi_channel = sorted(fund for fund, serials in serials_by_fund.items() if len(serials) >= 2)
    if multi_channel:
        return rng.choice(multi_channel)
    all_funds = sorted(
        {
            item[FUND_ID].strip()
            for item in all_items
            if isinstance(item.get(FUND_ID), str) and item[FUND_ID].strip()
        }
    )
    return rng.choice(all_funds) if all_funds else None


def _inject_share_item(new_data: dict[str, Any], pick: dict[str, Any]) -> None:
    """把挑中的产品项三字段注入 card.data, 各字段单独判断非空 (缺的不填)."""
    fund_id = pick.get(FUND_ID)
    if isinstance(fund_id, str) and fund_id.strip():
        new_data[PRODUCT_ID] = fund_id.strip()
    serial = pick.get(SERIAL_NO)
    if isinstance(serial, str) and serial.strip():
        new_data[BALANCE_SERIAL_NO] = serial.strip()
    uri_value = pick.get(URI)
    if isinstance(uri_value, str) and uri_value.strip():
        new_data["uri"] = uri_value.strip()


def enrich_test_cards(payload: Any) -> dict[str, Any]:
    root = require_object(payload, "input")
    allowed_root_keys = {"businessItems", "holdingDetail", "seed"}
    unsupported = sorted(set(root) - allowed_root_keys)
    if unsupported:
        raise EnrichTestError("input has unsupported fields: " + ", ".join(unsupported))

    raw_business_items = root.get("businessItems")
    if not isinstance(raw_business_items, list) or not raw_business_items:
        raise EnrichTestError("businessItems must be a non-empty array")

    holding_response = root.get("holdingDetail", [])

    seed = root.get("seed")
    if seed is not None and not isinstance(seed, int):
        raise EnrichTestError("seed must be an integer or omitted")
    rng = random.Random(seed)

    category_to_items = _category_to_items(holding_response)

    enriched_items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(raw_business_items):
        item = require_object(raw_item, f"businessItems[{index}]")
        card = require_object(item.get("card"), f"businessItems[{index}].card")
        card_id = require_string(card.get("cardId"), f"businessItems[{index}].card.cardId")
        data = card.get("data", {})
        if not isinstance(data, dict):
            raise EnrichTestError(f"businessItems[{index}].card.data must be an object")

        new_data = dict(data)
        if card_id == "ACC-19":
            all_items = [item for items in category_to_items.values() for item in items]
            picked = _pick_fund_id(all_items, rng)
            if picked is not None:
                new_data[PRODUCT_ID] = picked
        elif is_share_card(card_id):
            items = category_to_items.get(SHARE_PRODUCT_TYPES[card_id], [])
            pick = _pick_item(items, rng)
            if pick is not None:
                _inject_share_item(new_data, pick)

        enriched_card = dict(card)
        enriched_card["data"] = new_data
        enriched_item = dict(item)
        enriched_item["card"] = enriched_card
        enriched_items.append(enriched_item)

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inject test-mode share-card identifiers (productId/balanceSerialNo/uri) from queryHoldingDetail."
    )
    parser.add_argument(
        "--input", "-i", default=None,
        help="Combined input JSON (backward-compat; prefer --business-items + --holding-detail).",
    )
    parser.add_argument(
        "--business-items", default=None,
        help="Skeleton JSON path (output of build_result_skeleton.py).",
    )
    parser.add_argument(
        "--holding-detail", default=None,
        help="Raw queryHoldingDetail(type=1) MCP response JSON path.",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    parser.add_argument("--output", "-o", default="-", help="Output JSON path.")
    args = parser.parse_args(argv)

    try:
        if args.business_items and args.holding_detail:
            # Preferred: file-based mode — MCP raw data bypasses the LLM.
            with open_input(args.business_items) as source:
                skeleton = json.load(source)
            with open_input(args.holding_detail) as source:
                holding_detail = json.load(source)
            payload: dict[str, Any] = {
                "businessItems": skeleton["businessItems"],
                "holdingDetail": holding_detail,
            }
            if args.seed is not None:
                payload["seed"] = args.seed
        elif args.input:
            # Backward-compat: single combined JSON.
            with open_input(args.input) as source:
                payload = json.load(source)
        else:
            print(
                "enrich_test_cards: either --input or "
                "(--business-items + --holding-detail) is required",
                file=sys.stderr,
            )
            return 2

        write_output(args.output, enrich_test_cards(payload))
    except (OSError, json.JSONDecodeError, EnrichTestError) as error:
        print(f"enrich_test_cards: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
