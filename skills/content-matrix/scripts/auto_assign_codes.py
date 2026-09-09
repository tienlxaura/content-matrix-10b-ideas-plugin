#!/usr/bin/env python3
"""Replace the hand-guessed Formula/Pattern/Headline codes in
case-study-brief-specs.json with graph-informed picks: for each idea's real
Angle, take the highest-weight real COMPATIBLE_WITH neighbour per axis,
softly avoiding reusing the same code more than twice within one industry
(a cheap proxy for the product's own diversity floor).

This does not touch Angle or Type — those came from the audited landing-page
copy and stay fixed. Also fills in journey_stage / awareness_stage per
industry brief, which were missing from the first draft and were tanking
brief_fit/goal_fit unfairly.

Reference tool from the original 150-idea pass — JOURNEY_STAGE /
AWARENESS_STAGE below are editorial calls for those 15 specific industries.
Re-running as-is just re-derives the same codes; extending to a 16th
industry means adding its entry to both dicts first.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matrix_lib import MatrixData  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(ROOT, "case-study-brief-specs.json")
OUTPUT_PATH = os.path.join(ROOT, "case-study-brief-specs.json")  # overwrite in place

SOFT_CAP = 2  # discourage (not forbid) reusing the same code >2x per industry

# problem-stage industries vs solution/product-stage industries (editorial call
# based on where the audience actually is per the audit brief for each vertical)
JOURNEY_STAGE = {
    "saas-ai": "awareness", "giao-duc": "awareness", "fintech": "awareness",
    "bat-dong-san": "consideration", "beauty": "awareness", "healthcare": "awareness",
    "fitness": "awareness", "fnb": "consideration", "travel": "consideration",
    "retail": "consideration", "fashion": "consideration", "hr": "awareness",
    "manufacturing": "awareness", "creator": "awareness", "ev": "consideration",
}
AWARENESS_STAGE = {
    "saas-ai": "problem", "giao-duc": "problem", "fintech": "problem",
    "bat-dong-san": "solution", "beauty": "problem", "healthcare": "problem",
    "fitness": "problem", "fnb": "solution", "travel": "solution",
    "retail": "product", "fashion": "solution", "hr": "problem",
    "manufacturing": "problem", "creator": "problem", "ev": "solution",
}


def pick(data: MatrixData, angle: str, node_type: str, used: Counter, allowed=None) -> str:
    neighbours = data.positive_neighbors(angle, node_type)
    if allowed is not None:
        neighbours = {c: w for c, w in neighbours.items() if c in allowed}
    if not neighbours:
        neighbours = data.positive_neighbors(angle, node_type)  # capacity too tight — ignore it
    if not neighbours:
        raise RuntimeError("No positive neighbours for %s / %s" % (angle, node_type))
    ranked = sorted(neighbours.items(), key=lambda kv: -kv[1])
    # prefer the best-weighted option that is not yet over-used in this industry
    for code, _ in ranked:
        if used[code] < SOFT_CAP:
            used[code] += 1
            return code
    # everything reasonable is saturated — fall back to the single best option
    code = ranked[0][0]
    used[code] += 1
    return code


def formulas_fitting_capacity(data: MatrixData, ct_capacity: dict, type_code: str) -> set:
    """Content Formula codes whose step count fits the fixed Content Type's
    capacity — avoids the capacity_penalty for structural reasons that have
    nothing to do with which formula is otherwise the best graph match."""
    capacity = ct_capacity.get(type_code, 8)
    return {f["code"] for f in data.by_type["ContentFormula"]
            if len(f.get("structure") or []) <= capacity}


def main() -> int:
    with open(INPUT_PATH, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    data = MatrixData()

    for industry_id, industry_spec in spec["industries"].items():
        industry_spec["brief"]["journey_stage"] = JOURNEY_STAGE[industry_id]
        industry_spec["brief"]["awareness_stage"] = AWARENESS_STAGE[industry_id]

        used_formula, used_pattern, used_headline = Counter(), Counter(), Counter()
        for idea in industry_spec["ideas"]:
            angle = idea["angle"]
            fitting = formulas_fitting_capacity(data, data.overlay.get("ct_capacity", {}), idea["type"])
            idea["formula"] = pick(data, angle, "ContentFormula", used_formula, allowed=fitting)
            idea["pattern"] = pick(data, angle, "SuccessPattern", used_pattern)
            idea["headline"] = pick(data, angle, "HeadlineTemplate", used_headline)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)
    print("Rewrote", OUTPUT_PATH, "with graph-informed codes for all industries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
