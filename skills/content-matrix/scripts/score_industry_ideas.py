#!/usr/bin/env python3
"""Score the 150 landing-page case-study ideas with the real MatrixContent engine.

Reads case-study-brief-specs.json (15 industries, 10 pre-authored ideas each,
each idea already carrying its Angle/Formula/Pattern/Headline/Type codes) and
calls the same score_combo() rubric the product itself ships (see
references/scoring-and-diversity.md) against the real offline graph data.

This does NOT search for new combinations and does NOT invent copy — it only
scores combinations that were already chosen editorially, exactly the same
way select_combinations.py scores its own search candidates before ranking
them. Output: JSON id -> {score, rubric, penalties, blocked}.

case-study-brief-specs.json is the reproducibility record for the scores and
Formula/Pattern codes baked into the website's industry-briefs.ts /
industry-codes.ts — keep it in sync if either file changes by hand, and
re-run this script to confirm the displayed scores still match.

Usage: python scripts/score_industry_ideas.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matrix_lib import MatrixData, DataError  # noqa: E402
from select_combinations import (  # noqa: E402
    normalise_brief, brief_query, resolve_goals, score_pillars, build_context,
    score_combo, calibrate, TEXT_LOW_Q, TEXT_HIGH_Q,
)
from matrix_lib import rescale  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(ROOT, "case-study-brief-specs.json")
OUTPUT_PATH = os.path.join(ROOT, "case-study-scores-output.json")

EXPECTED_TYPE = {
    "angle": "ContentAngle", "formula": "ContentFormula", "pattern": "SuccessPattern",
    "headline": "HeadlineTemplate", "type": "ContentType",
}


def validate_codes(data: MatrixData, combo: dict, idea_id: str) -> list:
    problems = []
    for key, expected in EXPECTED_TYPE.items():
        code = combo[key]
        node = data.node(code)
        if node is None:
            problems.append("%s: code %s (%s) does not exist in catalog" % (idea_id, code, key))
        elif node.get("type") != expected:
            problems.append("%s: code %s (%s) is type %s, expected %s"
                             % (idea_id, code, key, node.get("type"), expected))
    return problems


def score_industry(data: MatrixData, industry_id: str, spec: dict) -> dict:
    raw_brief = spec["brief"]
    raw_brief.setdefault("topic", spec["brief"].get("topic", ""))
    brief = normalise_brief(raw_brief)
    query = data.text_index.query_tokens(brief_query(brief))
    goals = resolve_goals(data, brief)
    pillar_scores = score_pillars(data, brief, goals, query)

    ideas = spec["ideas"]
    angle_codes = sorted({idea["angle"] for idea in ideas})
    raw_text = {code: data.text_index.similarity(query, code) for code in angle_codes}
    low, high = calibrate(raw_text.values(), TEXT_LOW_Q, TEXT_HIGH_Q)
    angles_list = [{"code": code, "text": rescale(raw_text[code], low, high)} for code in angle_codes]

    context = build_context(data, brief, angles_list, pillar_scores, query)

    combos = {}
    for idea in ideas:
        combos[idea["id"]] = {
            "angle": idea["angle"], "formula": idea["formula"], "pattern": idea["pattern"],
            "headline": idea["headline"], "type": idea["type"],
        }

    # pass 1 — score once so pool-wide rarity frequencies are known
    first_pass = {iid: score_combo(data, combo, brief, goals, query, context)
                   for iid, combo in combos.items()}
    for axis, key in (("pattern_rarity", "pattern"), ("headline_rarity", "headline"),
                      ("angle_rarity", "angle")):
        counts = {}
        for entry in first_pass.values():
            code = entry["combo"][key]
            counts[code] = counts.get(code, 0) + 1
        top = max(counts.values()) if counts else 1
        context[axis] = {code: 1.0 - (count - 1) / max(top, 1) for code, count in counts.items()}

    # pass 2 — final, novelty-aware scores
    results = {}
    for iid, combo in combos.items():
        entry = score_combo(data, combo, brief, goals, query, context)
        results[iid] = {
            "score": entry["score"],
            "rubric": entry["rubric"],
            "penalties": [{"kind": p["kind"], "points": p["points"]} for p in entry["penalties"]],
            "blocked": entry["blocked"],
            "needs_evidence": entry["needs_evidence"],
        }
    return results


def main() -> int:
    with open(INPUT_PATH, "r", encoding="utf-8") as fh:
        spec = json.load(fh)

    try:
        data = MatrixData()
    except DataError as exc:
        print("DATA ERROR:", exc)
        return 1

    all_problems = []
    for industry_id, industry_spec in spec["industries"].items():
        for idea in industry_spec["ideas"]:
            combo = {k: idea[k] for k in ("angle", "formula", "pattern", "headline", "type")}
            all_problems.extend(validate_codes(data, combo, idea["id"]))
    if all_problems:
        print("CODE VALIDATION FAILED (%d problems):" % len(all_problems))
        for p in all_problems:
            print(" -", p)
        return 1
    print("Code validation OK: all 150 ideas reference real catalog codes of the right type.")

    output = {}
    for industry_id, industry_spec in spec["industries"].items():
        try:
            output.update(score_industry(data, industry_id, industry_spec))
        except DataError as exc:
            print("BRIEF ERROR in %s: %s" % (industry_id, exc))
            return 1

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    scores = [v["score"] for v in output.values()]
    blocked = [k for k, v in output.items() if v["blocked"]]
    print("Scored %d ideas. min=%.1f max=%.1f avg=%.1f" % (
        len(scores), min(scores), max(scores), sum(scores) / len(scores)))
    if blocked:
        print("BLOCKED (hard conflict — must fix combo):", blocked)
    print("Written to", OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
