#!/usr/bin/env python3
"""Test-mode helpers for the isolated card-test pipeline.

Imports only immutable constants from the shared ``account_contract``.
Everything here is part of the removable test-mode layer; the shared contract
and normal pipeline are untouched.
"""

from __future__ import annotations

# Share-level cards -> categoryCode of the 大类 to pick a random 份额 for.
# 份额级卡片是固定 cardId, 覆盖四大类; 组合 categoryCode="3" 无对应份额级卡片, 由 ACC-19 覆盖.
# 大类归属用于从 queryHoldingDetail 取该大类的 fundId, 再从 queryShareDetail 取份额 serialNo/uri.
SHARE_PRODUCT_TYPES: dict[str, str] = {
    "ACC-03": "1",  # 公募基金
    "ACC-05": "6",  # 投顾
    "ACC-06": "6",  # 投顾
    "ACC-08": "0",  # 货币
    "ACC-10": "4",  # 资管 (专户)
}


def is_share_card(card_id: str) -> bool:
    """True for the share-level cards that take a random 份额 from holdings."""
    return card_id in SHARE_PRODUCT_TYPES
