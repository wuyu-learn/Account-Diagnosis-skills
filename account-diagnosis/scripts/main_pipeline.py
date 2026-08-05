#!/usr/bin/env python3
"""Fast deterministic entry/finalizer for the normal account path.

The card-test path deliberately does not use this module. Test-prefixed input is
reported by ``prepare`` and rejected by ``finalize`` so the existing test-mode
runbook and scripts remain the only implementation of that path.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, TextIO

from build_result_skeleton import SkeletonError, build_result_skeleton
from compose_result import CompositionError, compose_result
from enrich_share_identifiers import EnrichmentError, enrich_share_identifiers
from normalize_input import NormalizeInputError, normalize_input


TEST_PREFIX = "问账户："
SUMMARY_ONLY = "summary_only"
DIAGNOSTIC = "diagnostic"

_DIAGNOSIS_RE = re.compile(
    r"账户诊断|诊断账户|账户.{0,6}诊断|账户体检|全面(?:分析|诊断)|"
    r"整体评价|找出?.{0,6}(?:主要问题|最值得关注)|主要有什么问题"
)
_CAUSE_RE = re.compile(r"为什么|为何|什么原因|原因(?:是|有|包括)|导致")
_RELATION_RE = re.compile(
    r"(?:是否|是不是).{0,16}(?:影响|拖累|贡献|相关|关联|重合|匹配)|"
    r"(?:结构|持仓|重仓|配置).{0,16}(?:与|和).{0,16}"
    r"(?:收益|回撤|归因).{0,8}(?:关系|关联)|"
    r"(?:重仓|头部持仓).{0,16}(?:是否|是不是|与).{0,12}(?:主要)?拖累"
)
_WATCHLIST_RE = re.compile(r"自选基金|自选|关注基金|关注列表")


class MainPipelineError(ValueError):
    """Raised when the normal-path pipeline input violates its contract."""


def _require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MainPipelineError(f"{path} must be an object")
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MainPipelineError(f"{path} must be a non-empty string")
    return value.strip()


def _query_texts(route_extract: dict[str, Any]) -> list[str]:
    texts = [str(route_extract.get("originalQuery", ""))]
    for scene in route_extract.get("scenes", []):
        if isinstance(scene, dict) and scene.get("scene") == "问账户":
            texts.append(str(scene.get("subQuery", "")))
    return [text for text in texts if text]


def is_test_input(route_extract: dict[str, Any]) -> bool:
    return any(text.startswith(TEST_PREFIX) for text in _query_texts(route_extract))


def classify_response_mode(
    route_extract: dict[str, Any], primary_intent: str | None = None
) -> str:
    """Classify with an explicit-trigger policy; everything else is summary-only."""
    query = " ".join(_query_texts(route_extract))
    if primary_intent == "watchlist_valuation" or _WATCHLIST_RE.search(query):
        return SUMMARY_ONLY
    if _DIAGNOSIS_RE.search(query) or _CAUSE_RE.search(query) or _RELATION_RE.search(query):
        return DIAGNOSTIC
    return SUMMARY_ONLY


def prepare(raw: Any) -> dict[str, Any]:
    route_extract = normalize_input(raw)
    test_mode = is_test_input(route_extract)
    result: dict[str, Any] = {
        "routeExtract": route_extract,
        "testMode": test_mode,
    }
    if not test_mode:
        result["responseMode"] = classify_response_mode(route_extract)
    return result


def _normalize_plan(value: Any) -> dict[str, Any]:
    plan = _require_object(value, "plan")
    allowed = {"primaryAccountIntent", "accountScenes", "cardPlans"}
    unsupported = sorted(set(plan) - allowed)
    if unsupported:
        raise MainPipelineError(
            "plan has unsupported fields (complexity is code-owned): "
            + ", ".join(unsupported)
        )
    missing = sorted(allowed - set(plan))
    if missing:
        raise MainPipelineError("plan is missing fields: " + ", ".join(missing))
    return plan


def _text_payload(value: Any, response_mode: str) -> dict[str, Any]:
    text = _require_object(value, "text")
    allowed = {"summaryNarrative", "conclusionNarrative", "followUp"}
    unsupported = sorted(set(text) - allowed)
    if unsupported:
        raise MainPipelineError("text has unsupported fields: " + ", ".join(unsupported))

    result: dict[str, Any] = {
        "summary": {
            "title": "账户诊断摘要" if response_mode == DIAGNOSTIC else "回答摘要",
            "narrative": _require_string(text.get("summaryNarrative"), "text.summaryNarrative"),
        },
        "followUp": text.get("followUp", []),
    }
    if response_mode == SUMMARY_ONLY:
        if "conclusionNarrative" in text:
            raise MainPipelineError("summary_only text must not include conclusionNarrative")
    else:
        result["conclusion"] = {
            "title": "综合结论",
            "narrative": _require_string(
                text.get("conclusionNarrative"), "text.conclusionNarrative"
            ),
        }
    return result


def finalize(payload: Any) -> dict[str, Any]:
    root = _require_object(payload, "input")
    allowed = {"routeExtract", "plan", "text", "shareBindings"}
    unsupported = sorted(set(root) - allowed)
    if unsupported:
        raise MainPipelineError("input has unsupported fields: " + ", ".join(unsupported))

    route_extract = _require_object(root.get("routeExtract"), "routeExtract")
    # Re-normalize to enforce the same route contract even for direct library callers.
    route_extract = normalize_input(route_extract)
    if is_test_input(route_extract):
        raise MainPipelineError("test-prefixed input must use the existing test-mode path")

    plan = _normalize_plan(root.get("plan"))
    primary_intent = _require_string(
        plan.get("primaryAccountIntent"), "plan.primaryAccountIntent"
    )
    response_mode = classify_response_mode(route_extract, primary_intent)
    complexity = "complex" if response_mode == DIAGNOSTIC else "simple"
    complexity_reason = (
        "命中明确的诊断、原因或关系分析诉求"
        if response_mode == DIAGNOSTIC
        else "未命中诊断触发条件，按直接事实问题回答"
    )
    full_plan = {
        "taskComplexity": complexity,
        "complexityReason": complexity_reason,
        "primaryAccountIntent": primary_intent,
        "accountScenes": plan["accountScenes"],
        "cardPlans": plan["cardPlans"],
    }
    skeleton = build_result_skeleton(full_plan)

    enrichment_input = {
        "businessItems": skeleton["businessItems"],
        "shareBindings": root.get("shareBindings", []),
    }
    business_items = enrich_share_identifiers(enrichment_input)["businessItems"]
    text_payload = _text_payload(root.get("text"), response_mode)

    compose_input = {
        "scene": "问账户",
        "taskComplexity": complexity,
        "primaryAccountIntent": primary_intent,
        "businessItems": business_items,
        **text_payload,
    }
    return compose_result(compose_input)


def open_input(path: str) -> TextIO:
    if path == "-":
        return sys.stdin
    return Path(path).open("r", encoding="utf-8")


def write_output(path: str, result: dict[str, Any]) -> None:
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if path == "-":
        sys.stdout.write(rendered)
    else:
        Path(path).write_text(rendered, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the normal account fast path.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "finalize"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--input", "-i", default="-", help="Input JSON/text path")
        sub.add_argument("--output", "-o", default="-", help="Output JSON path")
    args = parser.parse_args(argv)

    try:
        with open_input(args.input) as source:
            raw_text = source.read()
        try:
            raw: Any = json.loads(raw_text)
        except json.JSONDecodeError:
            raw = raw_text
        result = prepare(raw) if args.command == "prepare" else finalize(raw)
        write_output(args.output, result)
    except (
        OSError,
        json.JSONDecodeError,
        NormalizeInputError,
        MainPipelineError,
        SkeletonError,
        EnrichmentError,
        CompositionError,
    ) as error:
        print(f"main_pipeline: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
