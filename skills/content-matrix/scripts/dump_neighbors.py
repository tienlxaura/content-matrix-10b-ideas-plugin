#!/usr/bin/env python3
"""For each idea's Angle code, dump the graph's real top compatible
ContentFormula / SuccessPattern / HeadlineTemplate neighbours (by real edge
weight), so editorial code assignment can pick from graph-verified options
instead of guessing blind. Writes a compact text report.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matrix_lib import MatrixData  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(ROOT, "case-study-brief-specs.json")
OUTPUT_PATH = os.path.join(ROOT, "scratch_neighbors_report.txt")


def top_neighbors(data: MatrixData, angle: str, node_type: str, limit: int = 6):
    neighbours = data.positive_neighbors(angle, node_type)
    ranked = sorted(neighbours.items(), key=lambda kv: -kv[1])[:limit]
    return [(code, data.node(code)["name"], round(weight, 2)) for code, weight in ranked]


def main() -> int:
    with open(INPUT_PATH, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    data = MatrixData()

    lines = []
    for industry_id, industry_spec in spec["industries"].items():
        lines.append("=== %s ===" % industry_id)
        for idea in industry_spec["ideas"]:
            angle = idea["angle"]
            lines.append("%s  angle=%s (%s)" % (idea["id"], angle, data.node(angle)["name"]))
            for node_type, key in (("ContentFormula", "formula"), ("SuccessPattern", "pattern"),
                                    ("HeadlineTemplate", "headline")):
                neighbors = top_neighbors(data, angle, node_type)
                current = idea[key]
                current_ok = any(c == current for c, _, _ in neighbors)
                marker = "OK" if current_ok else "NOT-IN-TOP6"
                lines.append("  %s [current=%s %s]: %s" % (
                    node_type, current, marker,
                    ", ".join("%s(%s,%.2f)" % (c, n, w) for c, n, w in neighbors) or "(no positive edges)"
                ))
            lines.append("")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("Written", OUTPUT_PATH, "-", len(lines), "lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
