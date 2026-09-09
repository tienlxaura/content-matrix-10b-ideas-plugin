#!/usr/bin/env python3
"""Validate the offline snapshot and any result produced from it.

  python scripts/validate_matrixcontent.py                      # data only
  python scripts/validate_matrixcontent.py --result result.json # data + result
  python scripts/validate_matrixcontent.py --result r.json --min-count 10

Exit code 0 when every check passes, 1 when any check fails.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matrix_lib import (  # noqa: E402
    CATALOG_FILES, CODE_PATTERNS, DECLARED_RELATIONS, DataError, MatrixData,
    avoid_conflicts,
)

PLACEHOLDER_RE = re.compile(r"\[[^\]\n]{2,60}\]|\{\{[^}]+\}\}|<[a-zA-ZÀ-ỹ ]{2,40}>")

# Scaffolding that must never survive into published copy (copy-craft.md §9).
FORMULA_LEAKS = [
    "trong quá trình", "bài học hoặc điều kiện", "đặc điểm:", "cơ chế:", "lợi ích:",
    "bằng chứng:", "chẩn đoán:", "khuyến nghị và lý do", "chú ý:", "hứng thú:",
    "mong muốn:", "hành động:", "aida", "pas ", "p-a-s", "hook:", "body:", "cta:",
    "attention:", "interest:", "desire:", "vấn đề:", "giải pháp:", "trước:", "sau:",
]
# Empty marketing filler (copy-craft.md §10).
EMPTY_PHRASES = [
    "giải pháp toàn diện", "tối ưu trải nghiệm", "nâng tầm", "đồng hành cùng",
    "uy tín hàng đầu", "chất lượng vượt trội", "cam kết mang đến",
    "thấu hiểu khách hàng", "khẳng định vị thế", "kiến tạo giá trị",
    "trải nghiệm đẳng cấp", "sự lựa chọn hoàn hảo", "hàng đầu việt nam",
]
COPY_FIELDS = ("hook", "headline", "title", "final_headline", "opening",
               "copy", "content", "body", "first_lines")
REQUIRED_COMBO_FIELDS = ("rank", "score", "five_points", "rubric")
FIVE_POINTS = ("content_angle", "content_formula", "success_pattern",
               "headline_template", "content_type")
POINT_TYPES = {
    "content_angle": "ContentAngle", "content_formula": "ContentFormula",
    "success_pattern": "SuccessPattern", "headline_template": "HeadlineTemplate",
    "content_type": "ContentType",
}
DIVERSITY_FLOORS = {"content_angle": 4, "success_pattern": 4, "content_type": 3}


class Report:
    def __init__(self):
        self.checks = []

    def add(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append((name, ok, detail))
        return ok

    @property
    def failed(self):
        return [c for c in self.checks if not c[1]]

    def render(self) -> str:
        lines = []
        for name, ok, detail in self.checks:
            mark = "PASS" if ok else "FAIL"
            lines.append("[%s] %s%s" % (mark, name, ("  -- " + detail) if detail else ""))
        lines.append("")
        lines.append("%d/%d kiểm tra đạt." % (len(self.checks) - len(self.failed), len(self.checks)))
        return "\n".join(lines)


# --------------------------------------------------------------------------
# data snapshot
# --------------------------------------------------------------------------

def validate_data(data: MatrixData, report: Report) -> None:
    manifest = data.manifest
    counts = manifest.get("node_counts", {})

    for node_type, expected in counts.items():
        actual = len(data.by_type.get(node_type, []))
        report.add("Số node %s" % node_type, actual == expected,
                   "" if actual == expected else "kỳ vọng %d, thực tế %d" % (expected, actual))

    report.add("Tổng số node khớp manifest",
               len(data.nodes) == manifest.get("total_nodes"),
               "manifest %s, catalog %d" % (manifest.get("total_nodes"), len(data.nodes)))

    bad_codes = [c for c, node in data.nodes.items()
                 if not CODE_PATTERNS.get(node["type"], re.compile(r".*")).match(c)]
    report.add("Mọi mã đúng định dạng dải mã", not bad_codes,
               ", ".join(bad_codes[:6]) if bad_codes else "")

    orphans = [c for c, node in data.nodes.items()
               if node.get("parent_id") and node["parent_id"] not in data.nodes]
    report.add("Không có parent_id trỏ tới node thiếu", not orphans,
               ", ".join(orphans[:6]) if orphans else "")

    dangling = set()
    edge_total = 0
    for relation, table in data.relations.items():
        for source, targets in table.items():
            edge_total += len(targets)
            if source not in data.nodes:
                dangling.add(source)
            for target in targets:
                if target not in data.nodes:
                    dangling.add(target)
    report.add("Không có cạnh trỏ tới node thiếu", not dangling,
               ", ".join(sorted(dangling)[:6]) if dangling else "")

    # undirected relations are mirrored on load, so count the stored direction
    stats = {}
    index_path = os.path.join(data.data_dir, "graph-index.json")
    with open(index_path, "r", encoding="utf-8") as handle:
        stats = json.load(handle).get("relation_stats", {})
    report.add("Tổng số cạnh khớp manifest",
               sum(stats.values()) == manifest.get("total_edges"),
               "manifest %s, index %d" % (manifest.get("total_edges"), sum(stats.values())))

    report.add("Phiên bản index khớp manifest",
               data.graph_meta.get("data_version") == manifest.get("version"),
               "index %s, manifest %s" % (data.graph_meta.get("data_version"),
                                          manifest.get("version")))

    unknown = set(stats) - set(DECLARED_RELATIONS)
    report.add("Không có quan hệ ngoài từ vựng công bố", not unknown,
               ", ".join(sorted(unknown)) if unknown else "")

    missing_fields = []
    for node in data.nodes.values():
        for field in ("id", "code", "type", "name"):
            if not node.get(field):
                missing_fields.append("%s.%s" % (node.get("code", "?"), field))
    report.add("Mọi node có đủ trường bắt buộc", not missing_fields,
               ", ".join(missing_fields[:6]) if missing_fields else "")

    overlay = data.overlay
    report.add("Semantic overlay khai báo origin cục bộ",
               overlay.get("meta", {}).get("origin") == "local-heuristic",
               "origin=%s" % overlay.get("meta", {}).get("origin"))

    bad_refs = []
    for goal, spec in overlay.get("goal_affinity", {}).items():
        if goal not in data.nodes:
            bad_refs.append(goal)
        for pillar in spec.get("pillars", {}):
            if pillar not in data.nodes:
                bad_refs.append("%s->%s" % (goal, pillar))
    for stage, pillars in overlay.get("journey_stage_pillars", {}).items():
        bad_refs.extend("%s->%s" % (stage, p) for p in pillars if p not in data.nodes)
    for code in overlay.get("ct_capacity", {}):
        if code not in data.nodes:
            bad_refs.append(code)
    for rule in overlay.get("avoid_rules", []):
        for side in ("a", "b"):
            selector = rule[side]
            if selector.startswith("code:") and selector[5:] not in data.nodes:
                bad_refs.append(selector)
    report.add("Overlay không tham chiếu mã không tồn tại", not bad_refs,
               ", ".join(bad_refs[:6]) if bad_refs else "")

    known_tags = {t for node in data.nodes.values() for t in (node.get("tags") or [])}
    bad_tags = []
    for rule in overlay.get("avoid_rules", []):
        for side in ("a", "b"):
            selector = rule[side]
            if selector.startswith("tag:"):
                tag = selector.split(":", 2)[2]
                if tag not in known_tags:
                    bad_tags.append(selector)
    for spec in overlay.get("goal_affinity", {}).values():
        for section in ("sp_tags", "cf_tags", "ht_tags", "ct_tags"):
            bad_tags.extend(t for t in spec.get(section, {}) if t not in known_tags)
    report.add("Overlay không tham chiếu tag không tồn tại", not bad_tags,
               ", ".join(sorted(set(bad_tags))[:6]) if bad_tags else "")

    report.add("Mọi ContentType có sức chứa khai báo",
               all(node["code"] in overlay.get("ct_capacity", {})
                   for node in data.by_type["ContentType"]),
               "")

    # ---- enrichment layer ----
    ghost = [c for c in data.enrichment if c not in data.nodes]
    report.add("Enrichment không tham chiếu mã không tồn tại", not ghost,
               ", ".join(sorted(ghost)[:6]) if ghost else "")

    for node_type in ("ContentFormula", "SuccessPattern", "HeadlineTemplate",
                      "ContentType", "ContentAngle"):
        nodes = data.by_type[node_type]
        covered = [n for n in nodes if n["code"] in data.enrichment]
        report.add("Mọi %s có trường mô tả bổ sung" % node_type,
                   len(covered) == len(nodes),
                   "%d/%d" % (len(covered), len(nodes)))

    thin = [n["code"] for n in data.by_type["ContentFormula"] + data.by_type["SuccessPattern"]
            if len((n.get("ai_brief") or "").split()) < 12]
    report.add("Diễn giải công thức và mẫu hình đủ dài (>=12 từ)", not thin,
               ", ".join(thin[:6]) if thin else "")

    no_examples = [n["code"] for n in data.by_type["HeadlineTemplate"]
                   if len(n.get("examples") or []) < 10]
    report.add("Mọi mẫu tiêu đề có đủ 10 ví dụ", not no_examples,
               ", ".join(no_examples[:6]) if no_examples else
               "96/96 mẫu, %d ví dụ" % sum(len(n.get("examples") or [])
                                           for n in data.by_type["HeadlineTemplate"]))

    leftovers = [n["code"] for n in data.by_type["HeadlineTemplate"]
                 for ex in (n.get("examples") or []) if PLACEHOLDER_RE.search(ex)]
    report.add("Ví dụ tiêu đề không còn placeholder", not leftovers,
               ", ".join(sorted(set(leftovers))[:6]) if leftovers else "")

    industry = data.overlay.get("industry_profiles", {})
    bad_industry = [c for spec in industry.values() for c in spec.get("pillars", {})
                    if c not in data.nodes]
    bad_industry += [m for spec in industry.values() for m in spec.get("masters", [])
                     if m not in data.nodes]
    report.add("Hồ sơ ngành không tham chiếu mã không tồn tại", not bad_industry,
               ", ".join(sorted(set(bad_industry))[:6]) if bad_industry
               else "%d ngành" % len(industry))

    empty = data.missing_relations
    report.add("Ghi nhận quan hệ khai báo nhưng rỗng", True,
               ("%d quan hệ rỗng: %s" % (len(empty), ", ".join(empty))) if empty
               else "không có")


# --------------------------------------------------------------------------
# result
# --------------------------------------------------------------------------

def validate_result(data: MatrixData, result: dict, min_count: int, report: Report) -> None:
    combos = result.get("combinations", [])
    report.add("Kết quả có mảng combinations", bool(combos),
               "" if combos else "không tìm thấy hướng nào")
    if not combos:
        return

    report.add("Đủ số hướng yêu cầu", len(combos) >= min_count,
               "yêu cầu %d, có %d" % (min_count, len(combos)))

    missing_fields = [str(c.get("rank")) for c in combos
                      if any(f not in c for f in REQUIRED_COMBO_FIELDS)]
    report.add("Mọi hướng có đủ trường bắt buộc", not missing_fields,
               ", ".join(missing_fields[:6]) if missing_fields else "")

    unknown_codes, wrong_types = [], []
    for combo in combos:
        points = combo.get("five_points", {})
        for slot in FIVE_POINTS:
            entry = points.get(slot)
            if not entry or "code" not in entry:
                unknown_codes.append("%s:%s(thiếu)" % (combo.get("rank"), slot))
                continue
            code = entry["code"]
            node = data.node(code)
            if node is None:
                unknown_codes.append(code)
            elif node["type"] != POINT_TYPES[slot]:
                wrong_types.append("%s là %s, cần %s" % (code, node["type"], POINT_TYPES[slot]))
    report.add("Mọi mã trong kết quả đều tồn tại", not unknown_codes,
               ", ".join(unknown_codes[:6]) if unknown_codes else "")
    report.add("Mọi mã đúng loại node cho vị trí của nó", not wrong_types,
               "; ".join(wrong_types[:4]) if wrong_types else "")

    goal_codes = result.get("goal_resolution", {}).get("codes", [])
    violations = []
    for combo in combos:
        points = combo.get("five_points", {})
        codes = [points[s]["code"] for s in FIVE_POINTS
                 if points.get(s, {}).get("code") in data.nodes]
        if len(codes) != 5:
            continue
        for conflict in avoid_conflicts(data, codes, goal_codes):
            if conflict["severity"] == "hard":
                violations.append("#%s %s x %s" % (combo.get("rank"), conflict["a"], conflict["b"]))
    report.add("Không tổ hợp nào vi phạm AVOID_WITH", not violations,
               "; ".join(violations[:4]) if violations else "")

    fabricated = []
    for combo in combos:
        points = combo.get("five_points", {})
        for slot in FIVE_POINTS:
            entry = points.get(slot) or {}
            code, name = entry.get("code"), entry.get("name")
            node = data.node(code) if code else None
            if node and name and name != node["name"]:
                fabricated.append("%s: '%s' != '%s'" % (code, name, node["name"]))
    report.add("Không bịa tên node", not fabricated,
               "; ".join(fabricated[:4]) if fabricated else "")

    weight_errors = []
    for combo in combos:
        for pair, weight in (combo.get("edge_weights") or {}).items():
            if weight is None:
                continue
            left, right = pair.split("|", 1)
            actual = data.weight(left, right)
            if actual is None or abs(actual - weight) > 1e-6:
                weight_errors.append("%s: %s vs %s" % (pair, weight, actual))
    report.add("Trọng số cạnh khớp đồ thị", not weight_errors,
               "; ".join(weight_errors[:4]) if weight_errors else "")

    # diversity
    pairs_ok, worst = True, 5
    for i, a in enumerate(combos):
        for b in combos[i + 1:]:
            differ = sum(1 for slot in FIVE_POINTS
                         if (a.get("five_points", {}).get(slot) or {}).get("code")
                         != (b.get("five_points", {}).get(slot) or {}).get("code"))
            worst = min(worst, differ)
            if differ < 2:
                pairs_ok = False
    report.add("Mỗi cặp hướng khác nhau tối thiểu 2/5 thành phần", pairs_ok,
               "nhỏ nhất %d/5" % worst)

    constrained = bool(result.get("diversity", {}).get("constrained_by_brief"))
    for slot, floor in DIVERSITY_FLOORS.items():
        distinct = len({(c.get("five_points", {}).get(slot) or {}).get("code") for c in combos})
        target = 1 if constrained else floor
        report.add("Đa dạng %s" % slot, distinct >= target,
                   "%d khác nhau, cần %d%s" % (distinct, target,
                                               " (brief giới hạn)" if constrained else ""))

    # ---- copy-level checks, only for combos that already carry written copy ----
    def written(combo):
        return {f: combo[f] for f in COPY_FIELDS
                if isinstance(combo.get(f), str) and combo[f].strip()}

    with_copy = [c for c in combos if written(c)]

    leftovers = []
    for combo in combos:
        for field, value in written(combo).items():
            if PLACEHOLDER_RE.search(value):
                leftovers.append("#%s %s: %s" % (combo.get("rank"), field, value[:44]))
    report.add("Không còn placeholder trong chữ đã viết", not leftovers,
               "; ".join(leftovers[:4]) if leftovers
               else ("%d hướng có chữ" % len(with_copy) if with_copy
                     else "chưa có chữ nào trong kết quả"))

    leaks = []
    for combo in combos:
        for field, value in written(combo).items():
            low = value.lower()
            leaks.extend("#%s %s: '%s'" % (combo.get("rank"), field, marker)
                         for marker in FORMULA_LEAKS if marker in low)
    report.add("Không rò rỉ tên bước công thức vào bài", not leaks,
               "; ".join(leaks[:4]) if leaks else "")

    fillers = []
    for combo in combos:
        for field, value in written(combo).items():
            low = value.lower()
            fillers.extend("#%s '%s'" % (combo.get("rank"), phrase)
                           for phrase in EMPTY_PHRASES if phrase in low)
    report.add("Không dùng từ marketing rỗng", not fillers,
               "; ".join(sorted(set(fillers))[:4]) if fillers else "")

    if with_copy:
        long_hooks = []
        for combo in with_copy:
            hook = combo.get("hook") or combo.get("headline") or ""
            words = len(hook.split())
            if words > 14:
                long_hooks.append("#%s %d từ" % (combo.get("rank"), words))
        report.add("Hook đủ ngắn (≤14 từ)", not long_hooks,
                   ", ".join(long_hooks[:5]) if long_hooks else "")

    # ---- channel gating: a format the channel cannot carry must not appear ----
    strategy = result.get("strategy", {})
    banned = set(strategy.get("channel_media_banned", []))
    if banned:
        wrong = []
        for combo in combos:
            code = (combo.get("five_points", {}).get("content_type") or {}).get("code")
            if code and set(data.tags(code)) & banned:
                wrong.append("#%s %s" % (combo.get("rank"), data.label(code)))
        report.add("Không dùng định dạng bị kênh loại", not wrong,
                   "; ".join(wrong[:4]) if wrong else "banned=%s" % sorted(banned)[:4])

    provenance = result.get("provenance", {})
    report.add("Phiên bản dữ liệu của kết quả khớp snapshot",
               provenance.get("data_version") == data.manifest.get("version"),
               "kết quả %s, snapshot %s" % (provenance.get("data_version"),
                                            data.manifest.get("version")))


# --------------------------------------------------------------------------
# eval suite
# --------------------------------------------------------------------------

def _frontmatter_description() -> str:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SKILL.md")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return ""
    parts = text.split("---")
    return parts[1].lower() if len(parts) > 2 else ""


def run_evals(data: MatrixData, path: str, report: Report) -> None:
    import select_combinations as engine

    with open(path, "r", encoding="utf-8") as handle:
        suite = json.load(handle)

    description = _frontmatter_description()
    uncovered = [p for p in suite.get("activation_phrases", [])
                 if p.lower() not in description]
    report.add("Mọi cụm từ kích hoạt có trong description của SKILL.md", not uncovered,
               ", ".join(uncovered[:5]) if uncovered else "")

    for case in suite.get("cases", []):
        case_id = case["id"]
        expect = case.get("expect", {})
        try:
            result = engine.run(data, case["brief"], count=expect.get("count", 10))
        except Exception as exc:  # noqa: BLE001 - a crash is itself the finding
            report.add("eval %s chạy được" % case_id, False, "%s: %s" % (type(exc).__name__, exc))
            continue
        report.add("eval %s chạy được" % case_id, True)

        combos = result["combinations"]
        if "count" in expect:
            report.add("eval %s đủ %d hướng" % (case_id, expect["count"]),
                       len(combos) == expect["count"], "có %d" % len(combos))

        goal = result["goal_resolution"]
        if expect.get("goal_codes_any"):
            ok = any(code in expect["goal_codes_any"] for code in goal["codes"])
            report.add("eval %s mục tiêu hợp lý" % case_id, ok,
                       "chọn %s, kỳ vọng một trong %s" % (goal["codes"], expect["goal_codes_any"]))
        if expect.get("goal_method_any"):
            report.add("eval %s cách suy mục tiêu" % case_id,
                       goal["method"] in expect["goal_method_any"],
                       "method=%s" % goal["method"])

        masters = {c["master_pillar"]["code"] for c in combos}
        if expect.get("master_pillars_any"):
            report.add("eval %s phủ Master Pillar kỳ vọng" % case_id,
                       bool(masters & set(expect["master_pillars_any"])),
                       "có %s" % sorted(masters))

        pillars = {c["pillar"]["code"] for c in combos}
        if expect.get("pillars_subset_of"):
            extra = pillars - set(expect["pillars_subset_of"])
            report.add("eval %s tôn trọng pillar_hint" % case_id, not extra,
                       "ngoài ràng buộc: %s" % sorted(extra) if extra else "")

        if combos and "min_top_score" in expect:
            top = combos[0]["score"]
            report.add("eval %s điểm cao nhất >= %s" % (case_id, expect["min_top_score"]),
                       top >= expect["min_top_score"], "top=%.1f" % top)

        for axis, floor in (expect.get("min_distinct") or {}).items():
            entry = result["diversity"].get(axis, {})
            report.add("eval %s đa dạng %s >= %d" % (case_id, axis, floor),
                       entry.get("distinct", 0) >= floor, "có %s" % entry.get("distinct"))

        if "min_pairwise_difference" in expect:
            worst = result["diversity"]["min_pairwise_difference"]["value"]
            report.add("eval %s khác biệt từng cặp >= %d" % (case_id,
                                                             expect["min_pairwise_difference"]),
                       worst >= expect["min_pairwise_difference"], "nhỏ nhất %d/5" % worst)

        strategy = result.get("strategy", {})
        if expect.get("register"):
            report.add("eval %s register đúng" % case_id,
                       strategy.get("register") == expect["register"],
                       "được %s, cần %s" % (strategy.get("register"), expect["register"]))

        ct_codes = [c["five_points"]["content_type"]["code"] for c in combos]
        ht_codes = [c["five_points"]["headline_template"]["code"] for c in combos]

        for tag, floor in (expect.get("min_ct_tag") or {}).items():
            hits = sum(1 for code in ct_codes if tag in data.tags(code))
            report.add("eval %s có >= %d định dạng tag '%s'" % (case_id, floor, tag),
                       hits >= floor, "có %d" % hits)

        if expect.get("forbidden_ct_tags"):
            banned = set(expect["forbidden_ct_tags"])
            bad = [data.label(c) for c in ct_codes if set(data.tags(c)) & banned]
            report.add("eval %s không dùng định dạng bị cấm" % case_id, not bad,
                       "; ".join(sorted(set(bad))[:4]) if bad else "")

        if expect.get("forbidden_ht_tags"):
            banned = set(expect["forbidden_ht_tags"])
            bad = [data.label(c) for c in ht_codes if set(data.tags(c)) & banned]
            report.add("eval %s không dùng mẫu tiêu đề lệch register" % case_id, not bad,
                       "; ".join(sorted(set(bad))[:4]) if bad else "")

        if expect.get("max_ct_capacity"):
            cap = expect["max_ct_capacity"]
            table = data.overlay.get("ct_capacity", {})
            bad = [data.label(c) for c in ct_codes if table.get(c, 8) > cap]
            report.add("eval %s định dạng đủ ngắn cho kênh" % case_id, not bad,
                       "; ".join(sorted(set(bad))[:4]) if bad else "")

        if expect.get("no_hard_conflicts"):
            violations = []
            for combo in combos:
                codes = [combo["five_points"][s]["code"] for s in FIVE_POINTS]
                violations.extend(c for c in avoid_conflicts(data, codes, goal["codes"])
                                  if c["severity"] == "hard")
            report.add("eval %s không vi phạm AVOID_WITH" % case_id, not violations,
                       "%d vi phạm" % len(violations) if violations else "")

        # stability: the same brief must not reshuffle between identical runs
        repeat = engine.run(data, case["brief"], count=expect.get("count", 10))
        same = [c["five_points"]["content_angle"]["code"] for c in combos] == \
               [c["five_points"]["content_angle"]["code"] for c in repeat["combinations"]]
        report.add("eval %s kết quả ổn định khi chạy lại" % case_id, same,
                   "" if same else "hai lần chạy cho thứ tự khác nhau")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--result", help="file kết quả từ select_combinations.py")
    parser.add_argument("--evals", nargs="?", const="evals/eval-cases.json",
                        help="chạy bộ eval (mặc định evals/eval-cases.json)")
    parser.add_argument("--min-count", type=int, default=10,
                        help="số hướng tối thiểu kết quả phải có (mặc định 10)")
    parser.add_argument("--quiet", action="store_true", help="chỉ in các mục FAIL")
    args = parser.parse_args()

    report = Report()
    try:
        data = MatrixData()
    except DataError as exc:
        sys.stderr.write("LỖI: %s\n" % exc)
        return 1

    validate_data(data, report)

    if args.result:
        try:
            with open(args.result, "r", encoding="utf-8") as handle:
                result = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write("LỖI: không đọc được %s — %s\n" % (args.result, exc))
            return 1
        validate_result(data, result, args.min_count, report)

    if args.evals:
        path = args.evals
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
        try:
            run_evals(data, path, report)
        except OSError as exc:
            sys.stderr.write("LỖI: không đọc được bộ eval — %s\n" % exc)
            return 1

    if args.quiet:
        for name, ok, detail in report.failed:
            print("[FAIL] %s  -- %s" % (name, detail))
        print("%d/%d kiểm tra đạt." % (len(report.checks) - len(report.failed),
                                       len(report.checks)))
    else:
        print(report.render())
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
