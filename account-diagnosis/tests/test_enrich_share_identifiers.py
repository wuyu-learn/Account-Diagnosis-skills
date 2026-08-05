from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT_PATH = SCRIPT_DIR / "enrich_share_identifiers.py"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("enrich_share_identifiers", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

EnrichmentError = MODULE.EnrichmentError
enrich_share_identifiers = MODULE.enrich_share_identifiers
CARD_SPECS = MODULE.CARD_SPECS


def business_item(card_id: str, data: dict | None = None) -> dict:
    spec = CARD_SPECS[card_id]
    return {
        "section": {
            "type": spec["sectionType"],
            "title": spec["title"],
            "narrative": spec["narrative"],
        },
        "card": {
            "cardId": card_id,
            "dataMode": "deferred",
            "data": data if data is not None else {},
        },
    }


def payload(items: list[dict], bindings: list[dict] | None = None) -> dict:
    return {"businessItems": items, "shareBindings": bindings or []}


class EnrichShareIdentifiersTests(unittest.TestCase):
    def test_injects_serial_no_and_uri_into_share_card(self) -> None:
        items = [business_item("ACC-03"), business_item("ACC-01")]
        result = enrich_share_identifiers(
            payload(
                items,
                [
                    {
                        "cardId": "ACC-03",
                        "productId": "P1",
                        "balanceSerialNo": "S1",
                        "uri": "U1",
                    }
                ],
            )
        )
        cards = [item["card"] for item in result["businessItems"]]
        self.assertEqual(
            cards[0]["data"],
            {"productId": "P1", "balanceSerialNo": "S1", "uri": "U1"},
        )
        self.assertEqual(cards[1]["data"], {})
        # section payload is preserved
        self.assertEqual(cards[0]["cardId"], "ACC-03")
        self.assertIn("section", result["businessItems"][0])

    def test_passes_through_when_no_bindings(self) -> None:
        items = [business_item("ACC-03"), business_item("ACC-01")]
        result = enrich_share_identifiers(payload(items))
        self.assertEqual(result["businessItems"], items)

    def test_rejects_binding_for_non_share_card(self) -> None:
        with self.assertRaisesRegex(EnrichmentError, "share-level card"):
            enrich_share_identifiers(
                payload(
                    [business_item("ACC-01")],
                    [{"cardId": "ACC-01", "balanceSerialNo": "S1", "uri": "U1"}],
                )
            )

    def test_rejects_product_card_binding(self) -> None:
        with self.assertRaisesRegex(EnrichmentError, "share-level card"):
            enrich_share_identifiers(
                payload(
                    [business_item("ACC-19")],
                    [{"cardId": "ACC-19", "balanceSerialNo": "S1", "uri": "U1"}],
                )
            )

    def test_rejects_missing_or_empty_identifiers(self) -> None:
        with self.assertRaisesRegex(EnrichmentError, "non-empty string"):
            enrich_share_identifiers(
                payload(
                    [business_item("ACC-03")],
                    [{"cardId": "ACC-03", "balanceSerialNo": "", "uri": "U1"}],
                )
            )
        with self.assertRaisesRegex(EnrichmentError, "balanceSerialNo"):
            enrich_share_identifiers(
                payload(
                    [business_item("ACC-03")],
                    [{"cardId": "ACC-03", "uri": "U1"}],
                )
            )

    def test_rejects_unsupported_binding_fields(self) -> None:
        with self.assertRaisesRegex(EnrichmentError, "unsupported fields"):
            enrich_share_identifiers(
                payload(
                    [business_item("ACC-03")],
                    [
                        {
                            "cardId": "ACC-03",
                            "balanceSerialNo": "S1",
                            "uri": "U1",
                            "extra": "x",
                        }
                    ],
                )
            )

    def test_rejects_binding_for_absent_card(self) -> None:
        with self.assertRaisesRegex(EnrichmentError, "absent businessItems"):
            enrich_share_identifiers(
                payload(
                    [business_item("ACC-01")],
                    [{"cardId": "ACC-03", "balanceSerialNo": "S1", "uri": "U1"}],
                )
            )

    def test_ambiguous_candidates_leave_card_empty(self) -> None:
        result = enrich_share_identifiers(
            payload(
                [business_item("ACC-03")],
                [
                    {"cardId": "ACC-03", "balanceSerialNo": "S1", "uri": "U1"},
                    {"cardId": "ACC-03", "balanceSerialNo": "S2", "uri": "U2"},
                ],
            )
        )
        self.assertEqual(result["businessItems"][0]["card"]["data"], {})

    def test_rejects_existing_non_share_data(self) -> None:
        with self.assertRaisesRegex(EnrichmentError, "must only carry"):
            enrich_share_identifiers(
                payload(
                    [business_item("ACC-03", {"amount": "1"})],
                    [{"cardId": "ACC-03", "balanceSerialNo": "S1", "uri": "U1"}],
                )
            )


if __name__ == "__main__":
    unittest.main()
