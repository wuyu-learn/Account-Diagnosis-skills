#!/usr/bin/env python3
"""Shared deterministic contracts for account result generation."""

from __future__ import annotations

import re
from typing import Final


TASK_COMPLEXITIES: Final = frozenset({"simple", "complex"})

ACCOUNT_INTENTS: Final = frozenset(
    {
        "account_test",
        "account_overview",
        "holding_structure",
        "return_performance",
        "return_attribution",
        "watchlist_valuation",
    }
)

ACCOUNT_DIAGNOSIS_INTENTS: Final = frozenset(
    {
        "account_overview",
        "holding_structure",
        "return_performance",
        "return_attribution",
    }
)

SECTION_ORDER: Final = {
    "summary": 0,
    "account_test": 1,
    "account_overview": 2,
    "holding_structure": 3,
    "return_performance": 4,
    "return_attribution": 5,
    "watchlist_valuation": 6,
    "conclusion": 7,
}

IDENTITY_KEYS: Final = frozenset({"custNo", "accountName"})

DATE_TYPE_PATTERN: Final = re.compile(
    r"^(?:N|L|M0|M1|M3|M6|Y0|Y1|Y3|Y5|Y\d{4}|T)$"
)


def _spec(
    section_type: str,
    title: str,
    narrative: str,
    *,
    allowed_params: tuple[str, ...] = (),
    required_params: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "sectionType": section_type,
        "title": title,
        "narrative": narrative,
        "allowedParams": allowed_params,
        "requiredParams": required_params,
    }


CARD_SPECS: Final = {
    "ACC-01": _spec(
        "account_overview",
        "账户总资产",
        "下方卡片展示账户总资产及账户构成。",
    ),
    "ACC-02": _spec(
        "account_overview",
        "基金账户详情",
        "下方卡片展示基金账户整体情况。",
    ),
    "ACC-03": _spec(
        "account_overview",
        "基金持有详情",
        "下方卡片展示指定基金的持有情况。",
        allowed_params=("balanceSerialNo", "uri", "productId"),
    ),
    "ACC-04": _spec(
        "account_overview",
        "投顾账户详情",
        "下方卡片展示投顾账户整体情况。",
    ),
    "ACC-05": _spec(
        "account_overview",
        "投顾组合详情",
        "下方卡片展示指定投顾组合的账户和持仓情况。",
        allowed_params=("balanceSerialNo", "uri", "productId"),
    ),
    "ACC-06": _spec(
        "account_overview",
        "投顾调仓记录",
        "下方卡片展示指定投顾组合的调仓记录。",
        allowed_params=("balanceSerialNo", "uri", "productId"),
    ),
    "ACC-07": _spec(
        "account_overview",
        "货币账户详情",
        "下方卡片展示货币账户整体情况。",
    ),
    "ACC-08": _spec(
        "account_overview",
        "货币持有详情",
        "下方卡片展示指定货币基金的持有情况。",
        allowed_params=("balanceSerialNo", "uri", "productId"),
    ),
    "ACC-09": _spec(
        "account_overview",
        "专户账户详情",
        "下方卡片展示专户账户整体情况。",
    ),
    "ACC-10": _spec(
        "account_overview",
        "专户持有详情",
        "下方卡片展示指定专户产品的持有情况。",
        allowed_params=("balanceSerialNo", "uri", "productId"),
    ),
    "ACC-11": _spec(
        "holding_structure",
        "持仓明细",
        "下方卡片展示当前产品持仓明细。",
    ),
    "ACC-12": _spec(
        "holding_structure",
        "资产结构",
        "下方卡片展示资产类别、市场区域和行业风格分布。",
    ),
    "ACC-13-A": _spec(
        "return_performance",
        "账户收益总览",
        "下方卡片展示账户累计收益、收益率和收益走势。",
    ),
    "ACC-13-B": _spec(
        "return_performance",
        "账户收益总览 · 分年视角",
        "下方卡片展示账户自然年度收益表现。",
    ),
    "ACC-14": _spec(
        "return_performance",
        "收益明细日历",
        "下方卡片按日、月或年展示账户收益明细。",
    ),
    "ACC-15": _spec(
        "return_attribution",
        "收益归因",
        "下方卡片展示收益贡献项和拖累项。",
        allowed_params=("dateType",),
        required_params=("dateType",),
    ),
    "ACC-18": _spec(
        "watchlist_valuation",
        "自选基金估值",
        "下方卡片展示自选基金估值、当日涨跌和净值更新情况。",
    ),
    "ACC-19": _spec(
        "account_overview",
        "产品份额明细",
        "下方卡片展示指定产品的份额明细。",
        allowed_params=("productId",),
    ),
}


def is_watchlist_card(card_id: str) -> bool:
    return card_id == "ACC-18"


def is_valid_date_type(value: str) -> bool:
    return DATE_TYPE_PATTERN.fullmatch(value) is not None
