#!/usr/bin/env python3
"""Rank MatrixContent five-point combinations for a brief.

  python scripts/select_combinations.py --brief brief.json --count 10 --pretty

Reads a normalised brief (schema: references/ideation-workflow.md) and returns
ranked combinations of Content Angle -> Content Formula -> Success Pattern ->
Headline Template -> Content Type, with per-criterion scores, the real graph
edge weights behind them, conflicts, and diversity accounting.

The script chooses and scores. It never writes copy and never invents a code.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matrix_lib import (  # noqa: E402
    MISSING_EDGE_WEIGHT, WEIGHT_CEILING, WEIGHT_FLOOR, DataError, MatrixData,
    avoid_conflicts, calibrate, clamp, fold, rescale,
)

COMPLEXITY_SCORE = {"low": 0.35, "medium": 0.65, "high": 1.0}

# Similarity is rescaled against the run's own distribution (see calibrate).
TEXT_LOW_Q = 0.55
TEXT_HIGH_Q = 0.97

# search breadth
MAX_PILLARS = 14
MAX_PILLARS_PER_MASTER = 4
MAX_WILDCARD_PILLARS = 3
MAX_ANGLES = 44
MAX_ANGLES_PER_PILLAR = 4
# Hai cơ chế bổ sung đóng góp vào cùng một hồ ứng viên (xem choose_angles_*)
MAX_ANGLES_INDUSTRY = 18
MAX_ANGLES_RANDOM = 14
# Tỉ lệ đóng góp vào shortlist 30 ý tưởng, và sàn phải có mặt trong 10 cuối
MECHANISM_SHARE = {"brief": 0.50, "industry": 0.30, "random": 0.20}
MECHANISM_FLOOR = {"brief": 4, "industry": 2, "random": 1}
TOP_FORMULAS = 7
TOP_PATTERNS = 9
TOP_HEADLINES = 9
TOP_TYPES = 9
BEAM_WIDTH = 14

PAIR_PLAN = [
    ("angle", "formula", 1.5), ("angle", "pattern", 1.5),
    ("angle", "headline", 1.5), ("angle", "type", 1.5),
    ("formula", "pattern", 1.0), ("formula", "headline", 1.0),
    ("formula", "type", 1.0), ("pattern", "headline", 1.0),
    ("pattern", "type", 1.0), ("headline", "type", 1.0),
]

SIMILARITY_WEIGHTS = {
    "angle": 0.30, "pillar": 0.15, "pattern": 0.20, "pattern_tag": 0.10,
    "formula": 0.15, "headline": 0.05, "type": 0.05,
}

DIVERSITY_FLOORS = {"angle": 4, "pattern": 4, "type": 3, "pattern_tag": 4, "pillar": 3}


# --------------------------------------------------------------------------
# brief
# --------------------------------------------------------------------------

def normalise_brief(raw: dict) -> dict:
    def as_list(value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [str(v) for v in value if str(v).strip()]

    brief = {
        "topic": (raw.get("topic") or "").strip(),
        "brand": (raw.get("brand") or "").strip(),
        "industry": (raw.get("industry") or "").strip(),
        "product": (raw.get("product") or "").strip(),
        "audience": (raw.get("audience") or "").strip(),
        "insight": (raw.get("insight") or "").strip(),
        "marketing_goal": (raw.get("marketing_goal") or "").strip(),
        "goal_codes": as_list(raw.get("goal_codes")),
        "journey_stage": (raw.get("journey_stage") or "").strip().lower(),
        "awareness_stage": (raw.get("awareness_stage") or "").strip().lower(),
        "sophistication": raw.get("sophistication") or "",
        "channels": as_list(raw.get("channels")),
        "content_type_hint": as_list(raw.get("content_type_hint")),
        "tone": (raw.get("tone") or "").strip(),
        "assets": as_list(raw.get("assets")),
        "cta": (raw.get("cta") or "").strip(),
        "constraints": as_list(raw.get("constraints")),
        "avoid": as_list(raw.get("avoid")),
        "master_pillar_hint": as_list(raw.get("master_pillar_hint")),
        "pillar_hint": as_list(raw.get("pillar_hint")),
        "angle_hint": as_list(raw.get("angle_hint")),
    }
    if not brief["topic"]:
        raise DataError("Brief thiếu trường bắt buộc 'topic'.")
    return brief


def brief_query(brief: dict) -> str:
    return " ".join([
        brief["topic"], brief["topic"], brief["industry"], brief["product"],
        brief["audience"], brief["insight"], brief["insight"],
        brief["marketing_goal"], brief["cta"],
    ])


# --------------------------------------------------------------------------
# goal resolution (semantic fallback: MarketingGoal nodes carry no edges)
# --------------------------------------------------------------------------

def resolve_goals(data: MatrixData, brief: dict) -> dict:
    affinity = data.overlay["goal_affinity"]
    valid = [g for g in brief["goal_codes"] if g in affinity]
    unknown = [g for g in brief["goal_codes"] if g not in affinity]
    if valid:
        return {
            "codes": valid, "primary": valid[0],
            "weights": {g: (1.0 if i == 0 else 0.6) for i, g in enumerate(valid)},
            "method": "explicit", "unknown_codes": unknown,
            "semantic_fallback": False, "candidates": [],
        }

    text = fold(" ".join([brief["marketing_goal"], brief["cta"], brief["topic"],
                          brief["insight"], brief["audience"]]))
    stage = brief["journey_stage"]
    # An explicitly declared stage is a hard filter, not a 1.2 point nudge:
    # a brief that says "onboarding" must not resolve to a retention goal.
    family = set(data.overlay.get("stage_goal_families", {}).get(stage, []))
    scores = {}
    for code, spec in affinity.items():
        if family and code not in family:
            continue
        hits = sum(1 for kw in spec.get("keywords", []) if fold(kw) in text)
        node = data.node(code)
        node_text = fold(" ".join([node["name"], node.get("description", "")])) if node else ""
        overlap = sum(1 for word in set(node_text.split()) if len(word) > 3 and word in text)
        score = hits * 1.0 + overlap * 0.25
        if stage and spec.get("stage") == stage:
            score += 1.2
        if family and code in family:
            score += 0.4
        if score > 0:
            scores[code] = score
    if not scores:
        fallback = {"awareness": "RC01", "consideration": "RC05", "conversion": "RC12",
                    "onboarding": "RC13", "retention": "RC16", "advocacy": "RC17"}
        code = fallback.get(stage, "RC01")
        if family and code not in family:
            code = sorted(family)[0]
        return {
            "codes": [code], "primary": code, "weights": {code: 1.0},
            "method": "default", "unknown_codes": unknown, "semantic_fallback": True,
            "candidates": [], "note": "Không suy được mục tiêu từ brief; dùng mặc định theo giai đoạn.",
        }

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    codes = [ranked[0][0]]
    if len(ranked) > 1 and ranked[1][1] >= 0.55 * ranked[0][1]:
        codes.append(ranked[1][0])
    return {
        "codes": codes, "primary": codes[0],
        "weights": {g: (1.0 if i == 0 else 0.6) for i, g in enumerate(codes)},
        "method": "inferred", "unknown_codes": unknown, "semantic_fallback": True,
        "candidates": [{"code": c, "name": data.node(c)["name"], "score": round(s, 2)}
                       for c, s in ranked[:5]],
    }


def awareness_stage(data: MatrixData, brief: dict) -> str:
    declared = (brief.get("awareness_stage") or "").strip().lower()
    if declared in data.overlay.get("awareness_stage_ht_tags", {}):
        return declared
    mapping = data.overlay.get("journey_to_awareness", {})
    return mapping.get(brief["journey_stage"], "problem")


def awareness_fit(data: MatrixData, headline_code: str, stage: str) -> float:
    """Schwartz: what the reader already knows dictates the headline's form."""
    table = data.overlay.get("awareness_stage_ht_tags", {}).get(stage, {})
    if not table:
        return 0.5
    return max((table.get(tag, 0.0) for tag in data.tags(headline_code)), default=0.0)


def goal_affinity_value(data: MatrixData, goals: dict, section: str, code: str) -> float:
    """Best weighted affinity of a node's tags for the resolved goals."""
    best = 0.0
    tags = data.tags(code)
    for goal, weight in goals["weights"].items():
        table = data.overlay["goal_affinity"].get(goal, {}).get(section, {})
        if not table:
            continue
        if section == "pillars":
            best = max(best, table.get(code, 0.0) * weight)
        else:
            for tag in tags:
                best = max(best, table.get(tag, 0.0) * weight)
    return best


# --------------------------------------------------------------------------
# channels
# --------------------------------------------------------------------------

def resolve_channels(data: MatrixData, brief: dict) -> dict:
    """Map a brief's channel names onto declared channel profiles.

    v1 expanded each channel into a bag of tokens and accepted any overlap, so
    "tiktok" contained the token "social" and every text format matched it. The
    profile model gates on medium instead: a channel declares which Content Type
    media it can actually carry.
    """
    alias = {fold(k): v for k, v in data.overlay.get("channel_alias_map", {}).items()}
    profiles = data.overlay.get("channel_profiles", {})
    keys, tokens = [], set()
    for channel in brief["channels"]:
        folded = fold(channel)
        key = alias.get(folded)
        if key is None:
            key = next((v for k, v in alias.items() if k in folded or folded in k), None)
        if key and key in profiles and key not in keys:
            keys.append(key)
    for key in keys:
        tokens.update(fold(t) for t in profiles[key].get("tokens", []))
    primary, secondary, banned = set(), set(), set()
    for key in keys:
        profile = profiles[key]
        primary.update(profile.get("primary_media", []))
        secondary.update(profile.get("secondary_media", []))
        banned.update(profile.get("banned_media", []))
    # a medium allowed by one named channel is never banned by another
    banned -= (primary | secondary)
    caps = [profiles[k].get("max_capacity", 12) for k in keys]
    return {"keys": keys, "tokens": tokens, "primary": primary,
            "secondary": secondary, "banned": banned,
            "max_capacity": max(caps) if caps else 12,
            "unmapped": [c for c in brief["channels"] if not keys]}


def channel_fit(data: MatrixData, ct_code: str, channels: dict) -> float:
    """1.0 primary medium, 0.55 secondary, 0.0 banned. Neutral 0.6 with no channel."""
    if not channels["keys"]:
        return 0.6
    tags = set(data.tags(ct_code))
    if tags & channels["banned"]:
        return 0.0
    # A 20-minute webinar replay is a Video, but it is not a TikTok.
    capacity = data.overlay.get("ct_capacity", {}).get(ct_code, 8)
    if capacity > channels.get("max_capacity", 12):
        return 0.0
    node = data.node(ct_code)
    supported = {fold(c) for c in (node.get("suitable_channels") or [])}
    token_hit = bool(supported & channels["tokens"])
    if tags & channels["primary"]:
        return 1.0 if token_hit else 0.8
    if tags & channels["secondary"]:
        return 0.55 if token_hit else 0.4
    return 0.15


def brief_register(data: MatrixData, brief: dict, channels: dict) -> int:
    """Where the brand should sit on the intimate -> formal ladder."""
    scale = data.overlay.get("register_scale", {})
    table = {fold(k): v for k, v in data.overlay.get("register_by_industry", {}).items()}
    industry = fold(" ".join([brief["industry"], brief["product"], brief["topic"]]))
    level = None
    for key, name in table.items():
        if key and key in industry:
            level = scale.get(name)
            break
    if level is None:
        profiles = data.overlay.get("channel_profiles", {})
        levels = [scale.get(profiles[k].get("register"), 1) for k in channels["keys"]]
        level = min(levels) if levels else 1
    tone = fold(brief["tone"])
    if any(w in tone for w in ("than mat", "gan gui", "vui", "hai", "doi thuong", "ban be")):
        level = min(level, 1)
    if any(w in tone for w in ("trang trong", "nghiem tuc", "chuyen mon", "hoc thuat", "chuyen nghiep")):
        level = max(level, 2)
    return int(level)


def register_penalty(data: MatrixData, code: str, section: str, target: int) -> float:
    """0.0 when in register, growing to 1.0 as the gap widens."""
    table = data.overlay.get(section, {})
    levels = [table[t] for t in data.tags(code) if t in table]
    if not levels:
        return 0.0
    gap = min(abs(level - target) for level in levels)
    return clamp((gap - 0.5) / 2.0, 0.0, 1.0)


# --------------------------------------------------------------------------
# strategic selection
# --------------------------------------------------------------------------

def score_pillars(data: MatrixData, brief: dict, goals: dict, query: list) -> dict:
    stage_pillars = set(data.overlay["journey_stage_pillars"].get(brief["journey_stage"], []))
    hint_pillars = set(brief["pillar_hint"])
    hint_masters = set(brief["master_pillar_hint"])

    text_scores = {}
    for pillar in data.by_type["Pillar"]:
        code = pillar["code"]
        if hint_pillars and code not in hint_pillars:
            continue
        if hint_masters and pillar.get("parent_id") not in hint_masters:
            continue
        master = data.node(pillar.get("parent_id", ""))
        sim = data.text_index.similarity(query, code)
        if master:
            sim = max(sim, 0.4 * data.text_index.similarity(query, master["code"]))
        text_scores[code] = sim
    if not text_scores:
        raise DataError("Không còn Pillar nào sau khi áp dụng pillar_hint/master_pillar_hint.")

    # Calibrated against this run's spread, not max-normalised: one lexical
    # coincidence must not become 1.0.
    low, high = calibrate(text_scores.values(), TEXT_LOW_Q, TEXT_HIGH_Q)
    text_norm = {code: rescale(value, low, high) for code, value in text_scores.items()}
    scored = {}
    for code in text_scores:
        goal_value = goal_affinity_value(data, goals, "pillars", code)
        stage_value = 1.0 if code in stage_pillars else 0.0
        # Strategy leads. The catalog is deliberately domain-agnostic, so a brief's
        # wording is a weak signal at pillar level and only breaks ties here.
        scored[code] = {
            "total": 0.58 * goal_value + 0.22 * stage_value + 0.20 * text_norm[code],
            "goal": goal_value, "stage": stage_value, "text": text_norm[code],
            "eligible": goal_value > 0.0 or stage_value > 0.0,
        }
    return scored


def choose_pillars(data: MatrixData, scored: dict, forced: bool = False) -> list:
    """Goal- or stage-eligible pillars, plus a few high-affinity wildcards."""
    eligible = [c for c, e in scored.items() if e["eligible"]] if not forced else list(scored)
    if not eligible:
        eligible = list(scored)
    eligible.sort(key=lambda c: (-scored[c]["total"], c))

    chosen, per_master = [], {}
    for code in eligible:
        master = data.master_of(code)
        if per_master.get(master, 0) >= MAX_PILLARS_PER_MASTER:
            continue
        per_master[master] = per_master.get(master, 0) + 1
        chosen.append(code)
        if len(chosen) >= MAX_PILLARS - MAX_WILDCARD_PILLARS:
            break

    wildcards = sorted((c for c in scored if c not in chosen),
                       key=lambda c: (-scored[c]["text"], c))
    for code in wildcards[:MAX_WILDCARD_PILLARS]:
        if scored[code]["text"] > 0.0:
            chosen.append(code)
            scored[code]["wildcard"] = True
    return chosen[:MAX_PILLARS]


def choose_angles_random(data: MatrixData, brief: dict, pillars: list, pillar_scores: dict,
                         rng: random.Random, limit: int) -> list:
    """Cơ chế 1 — ngẫu nhiên có phân tầng.

    Bốc đều tay trên toàn bộ 624 góc, chỉ loại những góc không thể dùng. Đây là
    cơ chế duy nhất có thể chạm tới các góc mà hai cơ chế kia không bao giờ xét
    tới, nên nó là nguồn ý tưởng bất ngờ của cả hệ thống.
    """
    hint = set(brief["angle_hint"])
    pool = [a for a in data.by_type["ContentAngle"]
            if not hint or a["code"] in hint]
    if brief["pillar_hint"]:
        pool = [a for a in pool if a["parent_id"] in set(brief["pillar_hint"])]
    if brief["master_pillar_hint"]:
        masters = set(brief["master_pillar_hint"])
        pool = [a for a in pool if data.master_of(a["parent_id"]) in masters]
    if not pool:
        return []
    # phân tầng theo Master Pillar để một hệ quy chiếu không chiếm hết
    by_master = {}
    for a in pool:
        by_master.setdefault(data.master_of(a["parent_id"]), []).append(a)
    picked, masters = [], sorted(by_master)
    per_master = max(1, limit // max(len(masters), 1) + 1)
    for master in masters:
        bucket = sorted(by_master[master], key=lambda a: a["code"])
        rng.shuffle(bucket)
        picked.extend(bucket[:per_master])
    rng.shuffle(picked)
    return [{"code": a["code"], "score": 0.5, "text": 0.0, "source": "random"}
            for a in picked[:limit]]


def choose_angles_industry(data: MatrixData, brief: dict, pillars: list, pillar_scores: dict,
                           query: list, limit: int) -> list:
    """Cơ chế 2 — lọc theo ngành.

    Bỏ qua chủ đề và mục tiêu, chỉ hỏi: ngành này thường kể chuyện gì. Dùng hồ
    sơ ngành trong overlay, cộng khớp từ vựng với ngành và sản phẩm.
    """
    profiles = data.overlay.get("industry_profiles", {})
    industry_text = fold(" ".join([brief["industry"], brief["product"], brief["topic"]]))
    profile = None
    for key, spec in profiles.items():
        if fold(key) in industry_text:
            profile = spec
            break
    industry_query = data.text_index.query_tokens(
        " ".join([brief["industry"], brief["product"]]))

    raw = {}
    for angle in data.by_type["ContentAngle"]:
        code = angle["code"]
        if brief["angle_hint"] and code not in brief["angle_hint"]:
            continue
        pillar = angle["parent_id"]
        if brief["pillar_hint"] and pillar not in set(brief["pillar_hint"]):
            continue
        score = 0.0
        if profile:
            score += profile.get("pillars", {}).get(pillar, 0.0)
            if data.master_of(pillar) in profile.get("masters", []):
                score += 0.25
        if industry_query:
            score += 0.6 * data.text_index.similarity(industry_query, code)
        if score > 0:
            raw[code] = score
    if not raw:
        return []
    low, high = calibrate(raw.values(), 0.5, 0.97)
    ranked = sorted(raw.items(), key=lambda kv: (-kv[1], kv[0]))
    per_pillar, picked = {}, []
    for code, value in ranked:
        pillar = data.pillar_of(code)
        if per_pillar.get(pillar, 0) >= 3:
            continue
        per_pillar[pillar] = per_pillar.get(pillar, 0) + 1
        picked.append({"code": code, "score": rescale(value, low, high),
                       "text": 0.0, "source": "industry"})
        if len(picked) >= limit:
            break
    return picked


def choose_angles(data: MatrixData, brief: dict, pillars: list, pillar_scores: dict,
                  query: list) -> list:
    hint_angles = set(brief["angle_hint"])
    pillar_set = set(pillars)
    raw = {}
    for angle in data.by_type["ContentAngle"]:
        code = angle["code"]
        if hint_angles:
            if code not in hint_angles:
                continue
        elif angle.get("parent_id") not in pillar_set:
            continue
        raw[code] = data.text_index.similarity(query, code)
    if not raw:
        raise DataError("Không tìm được Content Angle nào phù hợp với ràng buộc của brief.")

    low, high = calibrate(raw.values(), TEXT_LOW_Q, TEXT_HIGH_Q)
    scored = []
    for code, value in raw.items():
        text_score = rescale(value, low, high)
        pillar_total = pillar_scores.get(data.pillar_of(code), {}).get("total", 0.0)
        scored.append((code, 0.40 * text_score + 0.60 * pillar_total, text_score))
    scored.sort(key=lambda item: (-item[1], item[0]))

    per_pillar, picked = {}, []
    for code, total, text_score in scored:
        pillar = data.pillar_of(code)
        # A wildcard pillar earned its place on wording alone; let it contribute
        # one angle for serendipity, never a whole cluster.
        cap = 1 if pillar_scores.get(pillar, {}).get("wildcard") else MAX_ANGLES_PER_PILLAR
        if not hint_angles and per_pillar.get(pillar, 0) >= cap:
            continue
        per_pillar[pillar] = per_pillar.get(pillar, 0) + 1
        picked.append({"code": code, "score": total, "text": text_score, "source": "brief"})
        if len(picked) >= MAX_ANGLES:
            break
    return picked


def rank_partners(data: MatrixData, goals: dict, angle: str, node_type: str,
                  limit: int, extra=None, veto=None) -> list:
    neighbours = data.positive_neighbors(angle, node_type)
    if not neighbours:
        return []
    section = {"ContentFormula": "cf_tags", "SuccessPattern": "sp_tags",
               "HeadlineTemplate": "ht_tags", "ContentType": "ct_tags"}[node_type]
    ranked = []
    for code, weight in neighbours.items():
        if veto and veto(code):
            continue
        affinity = goal_affinity_value(data, goals, section, code)
        bonus = extra(code) if extra else 0.0
        # Edge weight used to dominate at 0.55, so the same few high-weight
        # combinations won every brief. Brief-specific signal now leads.
        ranked.append((code, weight, 0.35 * weight + 0.45 * affinity + 0.20 * bonus))
    ranked.sort(key=lambda item: (-item[2], item[0]))
    return [(code, weight) for code, weight, _ in ranked[:limit]]


def beam_combinations(data: MatrixData, goals: dict, angle: str, brief: dict,
                      context: dict) -> list:
    hint = {fold(h) for h in brief["content_type_hint"]}
    channels = context["channels"]
    register = context["register"]
    stage = context["awareness_stage"]

    def type_bonus(code):
        score = channel_fit(data, code, channels)
        score -= 0.5 * register_penalty(data, code, "register_by_ct_tag", register)
        if hint:
            name = fold(data.node(code)["name"])
            score += 0.6 if any(h in name or name in h for h in hint) else 0.0
        return clamp(score, 0.0, 1.0)

    def type_veto(code):
        # A medium the channel cannot carry is not a low score, it is not an option.
        return channel_fit(data, code, channels) <= 0.0

    def headline_bonus(code):
        score = awareness_fit(data, code, stage)
        score -= 0.6 * register_penalty(data, code, "register_by_ht_tag", register)
        return clamp(score, 0.0, 1.0)

    formulas = rank_partners(data, goals, angle, "ContentFormula", TOP_FORMULAS)
    patterns = rank_partners(data, goals, angle, "SuccessPattern", TOP_PATTERNS)
    headlines = rank_partners(data, goals, angle, "HeadlineTemplate", TOP_HEADLINES,
                              extra=headline_bonus)
    types = rank_partners(data, goals, angle, "ContentType", TOP_TYPES,
                          extra=type_bonus, veto=type_veto)
    if not (formulas and patterns and headlines and types):
        return []

    beam = [({"angle": angle, "formula": code}, weight * 1.5, 1.5)
            for code, weight in formulas]
    for slot, options in (("pattern", patterns), ("headline", headlines), ("type", types)):
        expanded = []
        for partial, total, mass in beam:
            for code, angle_weight in options:
                combo = dict(partial)
                combo[slot] = code
                new_total, new_mass = total + angle_weight * 1.5, mass + 1.5
                for other, value in partial.items():
                    if other == "angle":
                        continue
                    edge = data.weight(value, code)
                    new_total += (edge if edge is not None else MISSING_EDGE_WEIGHT)
                    new_mass += 1.0
                expanded.append((combo, new_total, new_mass))
        expanded.sort(key=lambda item: (-item[1] / item[2], item[0]["formula"]))
        beam = expanded[:BEAM_WIDTH]
    return [combo for combo, _, _ in beam]


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def combo_edges(data: MatrixData, combo: dict) -> dict:
    edges, missing = {}, 0
    numerator = denominator = 0.0
    for left, right, mass in PAIR_PLAN:
        weight = data.weight(combo[left], combo[right])
        key = "%s|%s" % (combo[left], combo[right])
        if weight is None:
            missing += 1
            edges[key] = None
            weight = MISSING_EDGE_WEIGHT
        else:
            edges[key] = weight
        numerator += weight * mass
        denominator += mass
    return {"edges": edges, "missing": missing, "coherence": numerator / denominator}


def score_combo(data: MatrixData, combo: dict, brief: dict, goals: dict, query: list,
                context: dict) -> dict:
    angle, formula = combo["angle"], combo["formula"]
    pattern, headline, ctype = combo["pattern"], combo["headline"], combo["type"]
    pillar = data.pillar_of(angle)
    graph = combo_edges(data, combo)

    # 1 — brief and audience fit (20): lexical resonance plus whether this
    # pillar addresses the situation the brief's audience is actually in
    angle_text = context["angle_text_norm"].get(angle, 0.0)
    pillar_text = context["pillar_text_norm"].get(pillar, 0.0)
    goal_pillar = goal_affinity_value(data, goals, "pillars", pillar)
    if pillar in context["stage_pillars"]:
        situation = 1.0 if goal_pillar >= 0.5 else 0.8
    elif context["stage_masters"] and data.master_of(pillar) in context["stage_masters"]:
        situation = 0.45
    else:
        situation = 0.15
    # Lexical weight is deliberately capped. The catalog is domain-agnostic and
    # Vietnamese compounds collide across domains, so a word-level hit is
    # low-precision evidence and must never outrank strategic fit.
    c1 = (0.22 * angle_text + 0.13 * pillar_text + 0.65 * situation) * 20

    # 2 — marketing goal fit (15) — semantic fallback
    goal_cf = goal_affinity_value(data, goals, "cf_tags", formula)
    goal_sp = goal_affinity_value(data, goals, "sp_tags", pattern)
    goal_ht = goal_affinity_value(data, goals, "ht_tags", headline)
    goal_ct = goal_affinity_value(data, goals, "ct_tags", ctype)
    stage_hit = 1.0 if pillar in context["stage_pillars"] else 0.0
    aware = awareness_fit(data, headline, context["awareness_stage"])
    goal_raw = (0.26 * goal_pillar + 0.12 * goal_cf + 0.16 * goal_sp
                + 0.12 * goal_ht + 0.10 * goal_ct + 0.06 * stage_hit + 0.18 * aware)
    c2 = goal_raw * 15

    # 3 — internal consistency (20) — real graph edges
    c3 = rescale(graph["coherence"], WEIGHT_FLOOR, WEIGHT_CEILING) * 20

    # 4 — insight and reader value (15)
    insight_hit = context["insight_norm"].get(angle, 0.0)
    angle_node, pattern_node = data.node(angle), data.node(pattern)
    angle_depth = rescale(len(data.text_index.tokens.get(angle, [])), 6.0, 26.0)
    pattern_depth = rescale(len(data.text_index.tokens.get(pattern, [])), 4.0, 18.0)
    complexity = COMPLEXITY_SCORE.get(angle_node.get("complexity", "medium"), 0.65)
    c4 = (0.22 * insight_hit + 0.28 * angle_depth + 0.24 * pattern_depth
          + 0.26 * complexity) * 15

    # 5 — novelty and attention (10)
    rarity = (context["pattern_rarity"].get(pattern, 0.5) * 0.4
              + context["headline_rarity"].get(headline, 0.5) * 0.3
              + context["angle_rarity"].get(angle, 0.5) * 0.3)
    novelty_tags = data.overlay.get("novelty_tags", {})
    tag_hit = 0.0
    if set(data.tags(pattern)) & set(novelty_tags.get("sp_tags", [])):
        tag_hit += 0.6
    if set(data.tags(headline)) & set(novelty_tags.get("ht_tags", [])):
        tag_hit += 0.4
    c5 = (0.55 * rarity + 0.45 * min(tag_hit, 1.0)) * 10

    # 6 — channel and content type fit (10)
    fit = channel_fit(data, ctype, context["channels"])
    hint_score = 0.7
    if brief["content_type_hint"]:
        name = fold(data.node(ctype)["name"])
        hint_score = 1.0 if any(fold(h) in name or name in fold(h)
                                for h in brief["content_type_hint"]) else 0.15
    c6 = (0.60 * fit + 0.20 * goal_ct + 0.20 * hint_score) * 10

    # 7 — feasibility, evidence, credibility (10)
    effort_table = data.overlay.get("production_effort", {})
    effort = effort_table.get(data.node(ctype).get("format_specs", ""), 4)
    effort_score = 1.0 - rescale(effort, 1.0, 7.0)
    node_complexity = sum(
        COMPLEXITY_SCORE.get(data.node(code).get("complexity", "medium"), 0.65)
        for code in (angle, formula, pattern)) / 3.0
    asset_score = clamp(0.35 + 0.25 * len(brief["assets"]), 0.0, 1.0)
    c7 = (0.42 * effort_score + 0.28 * (1.0 - node_complexity) + 0.30 * asset_score) * 10

    rubric = {
        "brief_fit": round(c1, 2), "goal_fit": round(c2, 2), "coherence": round(c3, 2),
        "insight_value": round(c4, 2), "novelty": round(c5, 2),
        "channel_type_fit": round(c6, 2), "feasibility": round(c7, 2),
    }

    # penalties
    penalties, hard_block = [], False
    conflicts = avoid_conflicts(data, [angle, formula, pattern, headline, ctype], goals["codes"])
    for conflict in conflicts:
        if conflict["severity"] == "hard":
            hard_block = True
            penalties.append({"kind": "avoid_violation", "points": 25, "detail": conflict})
        elif conflict["severity"] == "penalty":
            penalties.append({"kind": "goal_format_mismatch",
                              "points": conflict.get("penalty", 3), "detail": conflict})
        else:
            penalties.append({"kind": "avoid_soft", "points": 8, "detail": conflict})

    steps = len(data.node(formula).get("structure") or [])
    capacity = data.overlay.get("ct_capacity", {}).get(ctype, 8)
    if steps > capacity:
        penalties.append({
            "kind": "capacity_penalty", "points": min(12, 3 * (steps - capacity)),
            "detail": {"formula_steps": steps, "type_capacity": capacity,
                       "reason": "Công thức %d bước vượt sức chứa của %s"
                                 % (steps, data.label(ctype)),
                       "source": "semantic_fallback"},
        })

    register_gap = max(
        register_penalty(data, headline, "register_by_ht_tag", context["register"]),
        register_penalty(data, ctype, "register_by_ct_tag", context["register"]),
    )
    if register_gap > 0.0:
        penalties.append({
            "kind": "register_mismatch", "points": round(10.0 * register_gap, 2),
            "detail": {"reason": "Giọng của %s / %s lệch với register mục tiêu (%s)"
                                 % (data.label(headline), data.label(ctype),
                                    context["register_name"]),
                       "source": "semantic_fallback"},
        })

    if graph["missing"]:
        penalties.append({
            "kind": "missing_edge_penalty", "points": min(9, 1.5 * graph["missing"]),
            "detail": {"missing_edges": graph["missing"], "source": "graph"},
        })

    hungry = data.overlay.get("evidence_hungry", {})
    needs_evidence = (
        set(data.tags(pattern)) & set(hungry.get("sp_tags", []))
        or set(data.tags(formula)) & set(hungry.get("cf_tags", []))
        or set(data.tags(headline)) & set(hungry.get("ht_tags", []))
    )
    if needs_evidence and not brief["assets"]:
        penalties.append({
            "kind": "evidence_gap", "points": 8,
            "detail": {"reason": "Tổ hợp cần bằng chứng nhưng brief không khai báo tài nguyên nào.",
                       "source": "semantic_fallback"},
        })

    for code in (angle, formula, pattern, headline, ctype):
        overlap = context["avoid_tokens"] & set(data.text_index.tokens.get(code, []))
        if len(overlap) >= 2:
            hard_block = True
            penalties.append({
                "kind": "constraint_violation", "points": 20,
                "detail": {"node": data.label(code), "matched_tokens": sorted(overlap),
                           "source": "semantic_fallback"},
            })

    total = clamp(sum(rubric.values()) - sum(p["points"] for p in penalties), 0.0, 100.0)
    return {
        "combo": combo, "rubric": rubric, "penalties": penalties,
        "conflicts": conflicts, "graph": graph, "blocked": hard_block,
        "score": round(total, 2), "needs_evidence": bool(needs_evidence),
    }


# --------------------------------------------------------------------------
# diversity
# --------------------------------------------------------------------------

def axes(data: MatrixData, combo: dict) -> dict:
    return {
        "angle": combo["angle"], "formula": combo["formula"],
        "pattern": combo["pattern"], "headline": combo["headline"],
        "type": combo["type"], "pillar": data.pillar_of(combo["angle"]),
        "pattern_tag": data.first_tag(combo["pattern"]),
    }


def differing_points(a: dict, b: dict) -> int:
    return sum(1 for key in ("angle", "formula", "pattern", "headline", "type")
               if a[key] != b[key])


def similarity(a: dict, b: dict) -> float:
    return sum(weight for key, weight in SIMILARITY_WEIGHTS.items() if a[key] == b[key])


def select_diverse(data: MatrixData, candidates: list, count: int, diversity: float,
                   rng: random.Random) -> tuple:
    lam = clamp(1.0 - diversity, 0.05, 0.95)
    pool = sorted(candidates, key=lambda c: (-c["score"], c["combo"]["angle"]))
    if not pool:
        return [], ["Không còn tổ hợp hợp lệ sau khi lọc xung đột."]
    top = pool[0]["score"] or 1.0
    for entry in pool:
        entry["axes"] = axes(data, entry["combo"])
        entry["norm"] = entry["score"] / top

    selected, warnings = [pool[0]], []
    remaining = pool[1:]
    while len(selected) < count and remaining:
        best, best_value, relaxed = None, None, lam
        while best is None and relaxed >= 0.05:
            for entry in remaining:
                if min(differing_points(entry["axes"], s["axes"]) for s in selected) < 2:
                    continue
                penalty = max(similarity(entry["axes"], s["axes"]) for s in selected)
                value = relaxed * entry["norm"] - (1.0 - relaxed) * penalty
                value += rng.uniform(0.0, 1e-6)
                if best_value is None or value > best_value:
                    best, best_value = entry, value
            if best is None:
                relaxed -= 0.05
        if best is None:
            warnings.append(
                "Chỉ tìm được %d hướng thỏa ràng buộc khác nhau tối thiểu 2/5 thành phần."
                % len(selected))
            break
        selected.append(best)
        remaining.remove(best)

    # top up under-represented axes without breaking the 2/5 rule
    for axis, floor in DIVERSITY_FLOORS.items():
        if len(selected) < count:
            break
        distinct = {s["axes"][axis] for s in selected}
        if len(distinct) >= floor:
            continue
        for entry in sorted(remaining, key=lambda c: -c["score"]):
            if entry["axes"][axis] in distinct:
                continue
            if min(differing_points(entry["axes"], s["axes"]) for s in selected) < 2:
                continue
            weakest = min(selected[1:], key=lambda s: s["score"], default=None)
            if weakest is None:
                break
            others = [s for s in selected if s is not weakest]
            if min(differing_points(entry["axes"], s["axes"]) for s in others) < 2:
                continue
            selected.remove(weakest)
            selected.append(entry)
            remaining.remove(entry)
            remaining.append(weakest)
            distinct.add(entry["axes"][axis])
            if len(distinct) >= floor:
                break

    selected.sort(key=lambda entry: -entry["score"])
    return selected, warnings


def enforce_mechanism_quota(data: MatrixData, selected: list, pool: list, count: int) -> list:
    """Bảo đảm danh sách cuối có mặt cả ba cơ chế, không phá ràng buộc 2/5."""
    for name, floor in MECHANISM_FLOOR.items():
        present = sum(1 for entry in selected if entry.get("source") == name)
        if present >= floor:
            continue
        available = [entry for entry in pool
                     if entry.get("source") == name and entry not in selected]
        available.sort(key=lambda e: -e["score"])
        for candidate in available:
            if present >= floor:
                break
            if min(differing_points(candidate["axes"], s["axes"]) for s in selected) < 2:
                continue
            # thay hướng yếu nhất thuộc cơ chế đang dư
            surplus = [entry for entry in selected
                       if sum(1 for x in selected if x.get("source") == entry.get("source"))
                       > MECHANISM_FLOOR.get(entry.get("source"), 0)]
            if not surplus:
                break
            weakest = min(surplus, key=lambda e: e["score"])
            others = [entry for entry in selected if entry is not weakest]
            if min(differing_points(candidate["axes"], s["axes"]) for s in others) < 2:
                continue
            selected.remove(weakest)
            selected.append(candidate)
            present += 1
    selected.sort(key=lambda entry: -entry["score"])
    return selected[:count]


def screen_feasibility(data: MatrixData, shortlist: list, brief: dict) -> list:
    """Sàng tính khả thi trên shortlist trước khi chốt danh sách bàn giao.

    Điểm rubric đo mức khớp; vòng này đo thứ khác: thương hiệu có làm nổi
    không, có bằng chứng chưa, có vi phạm ràng buộc không.
    """
    effort_table = data.overlay.get("production_effort", {})
    has_assets = bool(brief["assets"])
    for entry in shortlist:
        combo = entry["combo"]
        reasons, penalty = [], 0.0

        effort = effort_table.get(data.node(combo["type"]).get("format_specs", ""), 4)
        if effort >= 6:
            penalty += 2.0
            reasons.append("sản xuất rất nặng (%s)" % data.node(combo["type"])["format_specs"])
        elif effort >= 5:
            penalty += 1.0
            reasons.append("sản xuất nặng")

        if entry["needs_evidence"] and not has_assets:
            penalty += 3.0
            reasons.append("cần bằng chứng nhưng brief chưa khai tài nguyên nào")

        live = {"CT40", "CT46", "CT47", "CT55"}
        if combo["type"] in live:
            penalty += 2.5
            reasons.append("đòi thương hiệu tổ chức được sự kiện trực tiếp")

        if entry["conflicts"]:
            penalty += 1.5 * len(entry["conflicts"])
            reasons.append("%d xung đột mềm" % len(entry["conflicts"]))

        if entry["graph"]["missing"] >= 2:
            penalty += 1.0
            reasons.append("%d/10 cặp thiếu cạnh" % entry["graph"]["missing"])

        verdict = "loại" if penalty >= 6.0 else ("cân nhắc" if penalty >= 3.0 else "khả thi")
        entry["feasibility"] = {"verdict": verdict, "penalty": round(penalty, 2),
                                "reasons": reasons}
    shortlist.sort(key=lambda e: -(e["score"] - e["feasibility"]["penalty"]))
    return shortlist


def diversity_report(data: MatrixData, selected: list, constrained: bool) -> dict:
    report, shortfalls = {}, []
    for axis, floor in DIVERSITY_FLOORS.items():
        distinct = len({s["axes"][axis] for s in selected})
        target = 1 if constrained else floor
        report[axis] = {"distinct": distinct, "floor": target, "pass": distinct >= target}
        if distinct < target:
            shortfalls.append(axis)
    worst = 5
    for i, a in enumerate(selected):
        for b in selected[i + 1:]:
            worst = min(worst, differing_points(a["axes"], b["axes"]))
    report["min_pairwise_difference"] = {"value": worst if len(selected) > 1 else 5,
                                         "floor": 2, "pass": worst >= 2 or len(selected) < 2}
    report["constrained_by_brief"] = constrained
    report["shortfalls"] = shortfalls
    return report


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------

def describe(data: MatrixData, code: str) -> dict:
    node = data.node(code)
    out = {"code": code, "name": node["name"], "description": node.get("description", ""),
           "tags": node.get("tags", []), "complexity": node.get("complexity", "")}
    for field in ("direction", "role", "scope", "mechanism", "template", "format_specs"):
        if node.get(field):
            out[field] = node[field]
    if isinstance(node.get("structure"), list):
        out["structure"] = node["structure"]
    if node.get("suitable_channels"):
        out["suitable_channels"] = node["suitable_channels"]
    return out


def render(data: MatrixData, entry: dict, rank: int, explain: bool,
           mode: str = "default", brief: dict = None) -> dict:
    combo = entry["combo"]
    angle = combo["angle"]
    pillar, master = data.pillar_of(angle), data.master_of_angle(angle)
    angle_node = data.node(angle)
    formula_node = data.node(combo["formula"])
    pattern_node = data.node(combo["pattern"])
    headline_node = data.node(combo["headline"])
    type_node = data.node(combo["type"])

    payload = {
        "rank": rank,
        "score": entry["score"],
        "master_pillar": {"code": master, "name": data.node(master)["name"]},
        "pillar": {"code": pillar, "name": data.node(pillar)["name"],
                   "role": data.node(pillar).get("role", "")},
        "five_points": {
            "content_angle": describe(data, angle),
            "content_formula": describe(data, combo["formula"]),
            "success_pattern": describe(data, combo["pattern"]),
            "headline_template": describe(data, combo["headline"]),
            "content_type": describe(data, combo["type"]),
        },
        "rubric": entry["rubric"],
        "penalties": [{"kind": p["kind"], "points": round(p["points"], 2),
                       "reason": p["detail"].get("reason") or p["detail"].get("node")
                                 or str(p["detail"])} for p in entry["penalties"]],
        "graph_coherence": round(entry["graph"]["coherence"], 4),
        "missing_edges": entry["graph"]["missing"],
        "content_type_capacity": data.overlay.get("ct_capacity", {}).get(combo["type"]),
        "formula_steps": len(formula_node.get("structure") or []),
        "requires_evidence": entry["needs_evidence"],
        "flags": [],
    }
    payload["channel_fit"] = entry.get("channel_fit")
    payload["selection_mechanism"] = entry.get("source", "brief")
    if entry.get("feasibility"):
        payload["feasibility"] = entry["feasibility"]

    fields = ("ai_brief", "when_to_use", "avoid", "risk", "feel", "deliver", "examples")
    for slot, code in (("content_angle", angle), ("content_formula", combo["formula"]),
                       ("success_pattern", combo["pattern"]),
                       ("headline_template", combo["headline"]),
                       ("content_type", combo["type"])):
        node = data.node(code)
        for field in fields:
            if mode == "research" and field == "examples":
                # Ở chế độ research: ẩn ví dụ demo để ép AI sáng tạo mới
                continue
            if node.get(field):
                payload["five_points"][slot][field] = node[field]

    if mode == "research":
        struct_text = " -> ".join(formula_node.get("structure", [])) if formula_node.get("structure") else "mở đầu -> dẫn dắt -> chuyển đổi"
        mechanism_text = pattern_node.get("mechanism") or pattern_node.get("description") or pattern_node["name"]
        brief_topic = (brief.get("topic") if brief else "") or "chủ đề yêu cầu"
        brief_aud = (brief.get("audience") if brief else "") or "khách hàng mục tiêu"
        brief_ins = (brief.get("insight") if brief else "") or "sự thật ngầm hiểu của đối tượng"

        payload["research_framework"] = {
            "cau_hoi_research": {
                "cong_thuc_la_gi": {
                    "ten_cong_thuc": formula_node["name"],
                    "ma_so": formula_node.get("code", combo["formula"]),
                    "cau_truc_buoc": formula_node.get("structure", []),
                    "co_che_tam_ly": mechanism_text,
                    "ban_chat_giai_phau": (
                        f"Công thức {formula_node['name']} ({struct_text}) hoạt động dựa trên cơ chế tâm lý '{pattern_node['name']}'. "
                        f"Bản chất của cấu trúc này là kích hoạt sự đồng cảm, dẫn dắt nhận thức qua từng nấc thang cảm xúc "
                        f"để xóa bỏ rào cản phòng vệ tâm lý trước khi đưa ra lời kêu gọi."
                    ),
                },
                "cach_ap_dung_hieu_qua": {
                    "boi_canh_ap_dung": f"Áp dụng cho brief: '{brief_topic}' — nhắm tới '{brief_aud}'.",
                    "huong_dan_thuc_thi": (
                        f"Sử dụng góc tiếp cận '{angle_node['name']}' ({angle_node.get('direction') or angle_node.get('description', '')}) "
                        f"để chạm trúng insight '{brief_ins}'. Triển khai theo cấu trúc '{struct_text}' "
                        f"nhưng TUYỆT ĐỐI KHÔNG để lộ tên các bước công thức. Cần neo vào 1 khoảnh khắc hoặc chi tiết giác quan đời thực."
                    ),
                    "cam_bay_can_tranh": "Không dùng văn phong AI dịch máy (giải pháp toàn diện, tối ưu hóa...), không sao chép văn mẫu có sẵn, không đưa số liệu giả mạo.",
                }
            },
            "yeu_cau_sang_tao_bat_buoc": "CẤM sử dụng ví dụ mẫu và mô tả demo có sẵn từ hệ thống; ÉP AI sáng tạo nội dung mới 100% dựa trên khung ideas được trích xuất."
        }

    if mode == "deep":
        brief_fit_score = entry.get("rubric", {}).get("brief_fit", 15)
        relevance_pct = round((brief_fit_score / 20.0) * 100, 1)
        payload["deep_scorecard"] = {
            "prompt_relevance_pct": relevance_pct,
            "overall_effectiveness_score": round(entry["score"], 1),
            "selection_rationale": (
                f"Ý tưởng xếp hạng #{rank} với điểm tổng hợp {entry['score']:.1f}/100. "
                f"Độ tương thích cao ({relevance_pct}%) với yêu cầu gốc nhờ kết hợp góc '{angle_node['name']}' "
                f"và cơ chế '{pattern_node['name']}'."
            )
        }

    if entry["needs_evidence"]:
        payload["flags"].append("Cần bằng chứng thật; không được bịa số liệu hay dẫn chứng.")
    if entry["graph"]["missing"]:
        payload["flags"].append(
            "%d/10 cặp không có cạnh COMPATIBLE_WITH — phần ghép đó là semantic fallback."
            % entry["graph"]["missing"])
    for conflict in entry["conflicts"]:
        payload["flags"].append("Xung đột (%s): %s" % (conflict["source"], conflict["reason"]))
    if explain:
        payload["edge_weights"] = entry["graph"]["edges"]
        payload["axes"] = entry["axes"]
    return payload


def _calibrated(raw: dict) -> dict:
    low, high = calibrate(raw.values(), TEXT_LOW_Q, TEXT_HIGH_Q)
    return {code: rescale(value, low, high) for code, value in raw.items()}


def build_context(data: MatrixData, brief: dict, angles: list, pillar_scores: dict,
                  query: list) -> dict:
    insight_query = data.text_index.query_tokens(
        " ".join([brief["insight"], brief["audience"], brief["topic"]]))
    stage_pillars = set(data.overlay["journey_stage_pillars"].get(brief["journey_stage"], []))
    channels = resolve_channels(data, brief)
    register = brief_register(data, brief, channels)
    register_name = next((k for k, v in data.overlay.get("register_scale", {}).items()
                          if v == register), "đời thường")
    # Already on an absolute 0-1 scale; re-normalising to the pool max would
    # promote the least-bad match of a poorly matching pool.
    return {
        "angle_text_norm": {a["code"]: a["text"] for a in angles},
        "pillar_text_norm": {code: entry["text"] for code, entry in pillar_scores.items()},
        "insight_norm": _calibrated(
            {a["code"]: data.text_index.similarity(insight_query, a["code"])
             for a in angles}),
        "stage_pillars": stage_pillars,
        "stage_masters": {data.master_of(p) for p in stage_pillars},
        "channels": channels,
        "register": register,
        "register_name": register_name,
        "awareness_stage": awareness_stage(data, brief),
        "avoid_tokens": set(data.text_index.query_tokens(" ".join(brief["avoid"]))),
        "query": query,
        # filled in after the first scoring pass, when pool frequencies are known
        "pattern_rarity": {}, "headline_rarity": {}, "angle_rarity": {},
    }


def run(data: MatrixData, raw_brief: dict, count: int = 10, diversity: float = 0.35,
        seed: int = 0, explain: bool = False, pool_size: int = 30,
        mode: str = "default", target_count: int = 3, multiplier: int = 100) -> dict:
    """Full pipeline for one brief. Supports 'default', 'research', and 'deep' creative modes."""
    brief = normalise_brief(raw_brief)
    mode = (mode or "default").lower().strip()
    rng = random.Random(seed)
    query = data.text_index.query_tokens(brief_query(brief))
    goals = resolve_goals(data, brief)

    pillar_scores = score_pillars(data, brief, goals, query)
    pillars = choose_pillars(data, pillar_scores)
    angles = choose_angles(data, brief, pillars, pillar_scores, query)

    # Nếu ở chế độ chuyên sâu (deep mode): mở rộng độ phủ góc tiếp cận để trích xuất tập mẫu lớn (N * 100)
    ind_angle_limit = 30 if mode == "deep" else MAX_ANGLES_INDUSTRY
    rand_angle_limit = 30 if mode == "deep" else MAX_ANGLES_RANDOM

    # --- ba cơ chế chọn góc chạy song song, hợp nhất thành một hồ ứng viên ---
    generators = {
        "brief": angles,
        "industry": choose_angles_industry(data, brief, pillars, pillar_scores,
                                           query, ind_angle_limit),
        "random": choose_angles_random(data, brief, pillars, pillar_scores,
                                       rng, rand_angle_limit),
    }
    seen, merged = set(), []
    for name in ("brief", "industry", "random"):
        for angle in generators[name]:
            if angle["code"] in seen:
                continue
            seen.add(angle["code"])
            merged.append(angle)
    angles = merged

    context = build_context(data, brief, angles, pillar_scores, query)

    candidates, blocked = [], 0
    for angle in angles:
        for combo in beam_combinations(data, goals, angle["code"], brief, context):
            entry = score_combo(data, combo, brief, goals, query, context)
            entry["source"] = angle.get("source", "brief")
            if entry["blocked"]:
                blocked += 1
                continue
            candidates.append(entry)

    # novelty needs pool-wide frequencies, so score once, then refresh criterion 5
    for axis, key in (("pattern_rarity", "pattern"), ("headline_rarity", "headline"),
                      ("angle_rarity", "angle")):
        counts = {}
        for entry in candidates:
            code = entry["combo"][key]
            counts[code] = counts.get(code, 0) + 1
        top = max(counts.values()) if counts else 1
        context[axis] = {code: 1.0 - (count - 1) / max(top, 1) for code, count in counts.items()}
    rescored = []
    for entry in candidates:
        fresh = score_combo(data, entry["combo"], brief, goals, query, context)
        fresh["source"] = entry.get("source", "brief")
        rescored.append(fresh)
    candidates = [entry for entry in rescored if not entry["blocked"]]

    warnings = []
    final_output_count = target_count if mode == "deep" else count

    if mode == "deep":
        # Chế độ chuyên sâu: Trích xuất tập lớn M = target_count * multiplier (vd: 300, 500...)
        # Lọc khả thi trên toàn bộ tập ứng viên
        screened_pool = screen_feasibility(data, candidates, brief)
        survivors = [e for e in screened_pool if e["feasibility"]["verdict"] != "loại"]
        if not survivors:
            survivors = screened_pool or candidates

        # Sắp xếp theo điểm tổng hợp và chọn ra top N đa dạng nhất
        survivors.sort(key=lambda x: -x["score"])
        selected = []
        used_angles = set()
        used_formulas = set()
        for item in survivors:
            c_angle = item["combo"]["angle"]
            c_formula = item["combo"]["formula"]
            if c_angle in used_angles and len(selected) < final_output_count:
                continue
            selected.append(item)
            used_angles.add(c_angle)
            used_formulas.add(c_formula)
            if len(selected) >= final_output_count:
                break

        # Nếu còn thiếu, bổ sung các ý tưởng điểm cao kế tiếp
        if len(selected) < final_output_count:
            chosen_ids = {id(e) for e in selected}
            for item in survivors:
                if id(item) not in chosen_ids:
                    selected.append(item)
                    if len(selected) >= final_output_count:
                        break
        for item in selected:
            if "axes" not in item:
                item["axes"] = axes(data, item["combo"])
        shortlist = survivors[:max(pool_size, final_output_count * 3)]
    else:
        # Chế độ mặc định & research: phễu 3 cơ chế -> shortlist -> sàng khả thi -> danh sách bàn giao
        shortlist = []
        for name, share in MECHANISM_SHARE.items():
            bucket = [entry for entry in candidates if entry.get("source") == name]
            quota = max(1, int(round(pool_size * share)))
            picked, _ = select_diverse(data, bucket, quota, diversity, rng)
            shortlist.extend(picked)
        if len(shortlist) < pool_size:
            chosen = {id(entry) for entry in shortlist}
            rest = [entry for entry in candidates if id(entry) not in chosen]
            extra, _ = select_diverse(data, rest, pool_size - len(shortlist), diversity, rng)
            shortlist.extend(extra)

        shortlist = screen_feasibility(data, shortlist, brief)
        survivors = [entry for entry in shortlist if entry["feasibility"]["verdict"] != "loại"]
        if len(survivors) < final_output_count:
            survivors = shortlist

        selected, warn_div = select_diverse(data, survivors, final_output_count, diversity, rng)
        warnings.extend(warn_div)
        selected = enforce_mechanism_quota(data, selected, survivors, final_output_count)

    constrained = bool(brief["angle_hint"] or brief["pillar_hint"])
    if len(selected) < final_output_count:
        warnings.append("Yêu cầu %d hướng nhưng chỉ dựng được %d." % (final_output_count, len(selected)))
    if goals.get("unknown_codes"):
        warnings.append("Bỏ qua mã mục tiêu không tồn tại: %s"
                        % ", ".join(goals["unknown_codes"]))
    if context["channels"]["unmapped"]:
        warnings.append("Không nhận diện được kênh: %s — bỏ qua ràng buộc phương tiện."
                        % ", ".join(context["channels"]["unmapped"]))
    if data.missing_relations:
        warnings.append(
            "Đồ thị nguồn không có cạnh cho %d quan hệ đã khai báo (%s); "
            "tín hiệu tương ứng đến từ semantic overlay."
            % (len(data.missing_relations), ", ".join(data.missing_relations)))

    result = {
        "mode": mode,
        "provenance": data.provenance(),
        "brief": brief,
        "goal_resolution": {
            "codes": goals["codes"],
            "primary": {"code": goals["primary"], "name": data.node(goals["primary"])["name"]},
            "method": goals["method"],
            "semantic_fallback": goals["semantic_fallback"],
            "candidates": goals.get("candidates", []),
            "note": goals.get("note", ""),
        },
        "strategy": {
            "pillars_considered": [
                {"code": code, "name": data.node(code)["name"],
                 "master": data.master_of(code),
                 "score": round(pillar_scores[code]["total"], 3)}
                for code in pillars],
            "angles_considered": len(angles),
            "combinations_scored": len(candidates),
            "combinations_blocked": blocked,
            "shortlist_size": len(shortlist),
            "mechanism_mix": {name: sum(1 for a in angles if a.get("source") == name)
                              for name in ("brief", "industry", "random")},
            "feasibility_screen": {v: sum(1 for e in shortlist
                                          if e["feasibility"]["verdict"] == v)
                                   for v in ("khả thi", "cân nhắc", "loại")},
            "channels_resolved": context["channels"]["keys"],
            "channel_media_primary": sorted(context["channels"]["primary"]),
            "channel_media_banned": sorted(context["channels"]["banned"]),
            "register": context["register_name"],
            "awareness_stage": context["awareness_stage"],
        },
        "must_use_assets": brief["assets"],
        "editorial_constraints": brief["constraints"],
        "combinations": [render(data, entry, i + 1, explain, mode=mode, brief=brief)
                         for i, entry in enumerate(selected)],
        "diversity": diversity_report(data, selected, constrained) if selected else {},
        "warnings": warnings,
    }

    if mode == "deep":
        result["deep_evaluation"] = {
            "mode": "deep",
            "target_ideas_requested": target_count,
            "multiplier": multiplier,
            "total_candidates_extracted": len(candidates),
            "search_and_context_enrichment": {
                "topic_tokens_matched": len(query),
                "pillars_explored": len(pillars),
                "master_pillars_coverage": sorted(list({data.master_of(p) for p in pillars if p in data.nodes})),
                "angles_evaluated": len(angles),
            },
            "evaluation_funnel": {
                "candidates_extracted": len(candidates),
                "screened_viable": len(survivors),
                "curated_top_ideas": len(selected),
            },
            "evaluation_criteria": [
                "Độ tương thích sâu sắc với prompt gốc (Relevance Fit: topic, audience, insight)",
                "Hiệu quả tâm lý và tiềm năng chuyển đổi (Effectiveness & Psychology Conversion)",
                "Tính khả thi triển khai trên kênh và tài nguyên thực tế (Feasibility)"
            ]
        }

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--brief", required=True,
                        help="đường dẫn file brief JSON ('-' để đọc stdin)")
    parser.add_argument("--count", type=int, default=10, help="số hướng cần trả về (mặc định 10)")
    parser.add_argument("--diversity", type=float, default=0.35, help="0.0-1.0, mặc định 0.35")
    parser.add_argument("--seed", type=int, default=0, help="hạt ngẫu nhiên cho tie-break")
    parser.add_argument("--explain", action="store_true", help="kèm trọng số từng cạnh")
    parser.add_argument("--pretty", action="store_true", help="JSON xuống dòng")
    parser.add_argument("--pool", type=int, default=30,
                        help="số ý tưởng dựng ở vòng shortlist trước khi sàng (mặc định 30)")
    parser.add_argument("--mode", default="default", choices=["default", "research", "deep"],
                        help="chế độ sáng tạo: default, research, deep")
    parser.add_argument("--target-count", type=int, default=3,
                        help="số ý tưởng mong muốn nhận ở chế độ deep (mặc định 3)")
    parser.add_argument("--multiplier", type=int, default=100,
                        help="hệ số nhân ứng viên ở chế độ deep (mặc định 100)")
    parser.add_argument("--out", help="ghi kết quả ra file")
    args = parser.parse_args()

    try:
        raw = json.load(sys.stdin) if args.brief == "-" else json.load(
            open(args.brief, "r", encoding="utf-8"))
        data = MatrixData()
        result = run(data, raw, args.count, args.diversity, args.seed, args.explain,
                     args.pool, mode=args.mode, target_count=args.target_count,
                     multiplier=args.multiplier)
    except (DataError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write("LỖI: %s\n" % exc)
        return 1

    text = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        sys.stderr.write("Đã ghi %d hướng ra %s\n" % (len(result["combinations"]), args.out))
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
