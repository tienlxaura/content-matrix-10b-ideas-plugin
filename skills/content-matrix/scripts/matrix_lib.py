"""Shared loading, text and graph utilities for the MatrixContent skill.

Standard library only. No network access happens here; sync_matrixcontent.py owns
all HTTP. Every other script reads the offline snapshot in ../data.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import unicodedata
from collections import defaultdict

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("CONTENT_MATRIX_DATA_DIR", os.path.join(SKILL_ROOT, "data"))
CATALOG_DIR = os.path.join(DATA_DIR, "catalogs")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CATALOG_FILES = {
    "MasterPillar": "master-pillars.json",
    "Pillar": "pillars.json",
    "ContentAngle": "content-angles.json",
    "ContentFormula": "content-formulas.json",
    "SuccessPattern": "success-patterns.json",
    "HeadlineTemplate": "headline-templates.json",
    "ContentType": "content-types.json",
    "MarketingGoal": "marketing-goals.json",
}

# The nine relations MatrixContent publishes in its vocabulary.
DECLARED_RELATIONS = [
    "CONTAINS", "BELONGS_TO", "COMPATIBLE_WITH", "RECOMMENDED_FOR",
    "AMPLIFIES", "EXPRESSED_AS", "DELIVERED_AS", "AVOID_WITH", "PRIORITIZED_BY",
]
# Relations whose edges should be readable from either endpoint.
UNDIRECTED_RELATIONS = {"COMPATIBLE_WITH", "AVOID_WITH"}
# Relations that express positive affinity and may drive combination search.
POSITIVE_RELATIONS = [
    "COMPATIBLE_WITH", "RECOMMENDED_FOR", "AMPLIFIES", "EXPRESSED_AS",
    "DELIVERED_AS", "PRIORITIZED_BY",
]

CODE_PATTERNS = {
    "MasterPillar": re.compile(r"^MP0[1-5]$"),
    "Pillar": re.compile(r"^(CJ|BR|MM|JT|CO)\d{2}$"),
    "ContentAngle": re.compile(r"^(CJ|BR|MM|JT|CO)\d{2}-A\d{2}$"),
    "ContentFormula": re.compile(r"^CF\d{2}$"),
    "SuccessPattern": re.compile(r"^MH\d{2}$"),
    "HeadlineTemplate": re.compile(r"^HT\d{3}$"),
    "ContentType": re.compile(r"^CT\d{2}$"),
    "MarketingGoal": re.compile(r"^RC\d{2}$"),
}

MISSING_EDGE_WEIGHT = 0.35
WEIGHT_FLOOR = 0.40
WEIGHT_CEILING = 0.95


class DataError(RuntimeError):
    """Raised when the offline snapshot is missing or inconsistent."""


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------

_COMBINING = dict.fromkeys(
    c for c in range(0x0300, 0x036F + 1)
)


def fold(text: str) -> str:
    """Lowercase and strip Vietnamese diacritics for robust matching."""
    if not text:
        return ""
    text = text.lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = text.translate(_COMBINING)
    return unicodedata.normalize("NFC", text)


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str, stopwords: set) -> list:
    return [t for t in _TOKEN_RE.findall(fold(text)) if len(t) > 1 and t not in stopwords]


def bigrams(tokens: list) -> set:
    return {tokens[i] + "_" + tokens[i + 1] for i in range(len(tokens) - 1)}


# Vietnamese words are mostly two syllables, so a folded unigram is a syllable,
# not a word: "sở hữu trí tuệ" and "toán trí tuệ" share four of them by accident.
# Bigrams carry the real lexical signal; unigrams only break ties.
UNIGRAM_WEIGHT = 0.30
BIGRAM_WEIGHT = 1.00
# Added to a document's norm before dividing; roughly half a median entry.
LENGTH_SMOOTHING = 45.0
# Shared bigrams needed before a lexical match is treated as fully corroborated.
CORROBORATION = 2.0


class TextIndex:
    """IDF-weighted similarity over the catalog corpus, bigram-dominant."""

    def __init__(self, documents: dict, stopwords: set):
        self.stopwords = stopwords
        self.tokens = {}
        self.features = {}
        df = defaultdict(int)
        for key, text in documents.items():
            toks = tokenize(text, stopwords)
            self.tokens[key] = toks
            feats = self._features(toks)
            self.features[key] = feats
            for feature in feats:
                df[feature] += 1
        n = max(len(documents), 1)
        self.idf = {f: math.log(1.0 + n / (1.0 + c)) for f, c in df.items()}
        self._default_idf = math.log(1.0 + n)
        self._norms = {k: self._norm(v) for k, v in self.features.items()}

    @staticmethod
    def _features(tokens: list) -> dict:
        feats = {}
        for token in set(tokens):
            feats["u:" + token] = UNIGRAM_WEIGHT
        for gram in bigrams(tokens):
            feats["b:" + gram] = BIGRAM_WEIGHT
        return feats

    def weight(self, feature: str) -> float:
        return self.idf.get(feature, self._default_idf)

    def _norm(self, feats: dict) -> float:
        return sum(w * self.weight(f) for f, w in feats.items()) or 1.0

    def query_tokens(self, text: str) -> list:
        return tokenize(text, self.stopwords)

    def similarity(self, query_tokens: list, key: str) -> float:
        """How much of a node's distinctive content the brief covers, in [0, 1].

        Asymmetric on purpose. Cosine would divide by the query norm, so a
        detailed brief would score lower than a terse one against the very same
        node — the opposite of what a brief's richness should do.
        """
        doc = self.features.get(key)
        if not doc or not query_tokens:
            return 0.0
        query = self._features(query_tokens)
        shared = set(query) & set(doc)
        if not shared:
            return 0.0
        covered = sum(doc[f] * self.weight(f) for f in shared)
        # One shared bigram is a coincidence -- Vietnamese compounds collide
        # across unrelated domains ("nội dung nổi bật" vs "con nổi bật"). Two or
        # more corroborate each other, so a lone hit only counts half.
        matched_bigrams = sum(1 for f in shared if f.startswith("b:"))
        confidence = clamp(0.5 + 0.5 * matched_bigrams / CORROBORATION, 0.5, 1.0)
        # Smoothing keeps a single lucky bigram from saturating a short entry.
        score = covered / (self._norms.get(key, 1.0) + LENGTH_SMOOTHING)
        return clamp(score * confidence, 0.0, 1.0)


def normalize_scores(values: dict) -> dict:
    """Scale a mapping of raw scores into [0, 1] by its own max."""
    if not values:
        return {}
    top = max(values.values())
    if top <= 0:
        return {k: 0.0 for k in values}
    return {k: v / top for k, v in values.items()}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def percentile(sorted_values: list, quantile: float) -> float:
    if not sorted_values:
        return 0.0
    index = int(round(quantile * (len(sorted_values) - 1)))
    return sorted_values[clamp(index, 0, len(sorted_values) - 1)]


def calibrate(values, low_q: float = 0.55, high_q: float = 0.97) -> tuple:
    """Derive rescaling bounds from the run's own similarity distribution.

    Absolute thresholds cannot work here: a rich brief and a two-word brief
    produce different similarity scales against the same catalog.
    """
    ordered = sorted(values)
    low, high = percentile(ordered, low_q), percentile(ordered, high_q)
    if high - low < 1e-6:
        high = low + 1e-6
    return low, high


def rescale(value: float, low: float, high: float) -> float:
    """Map value from [low, high] onto [0, 1], clamped."""
    if high <= low:
        return 0.0
    return clamp((value - low) / (high - low), 0.0, 1.0)


# --------------------------------------------------------------------------
# data access
# --------------------------------------------------------------------------

def _read_json(path: str):
    if not os.path.exists(path):
        raise DataError(
            "Thiếu file dữ liệu: %s\nChạy: python scripts/sync_matrixcontent.py" % path
        )
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class MatrixData:
    """The offline MatrixContent snapshot plus the local semantic overlay."""

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.manifest = _read_json(os.path.join(data_dir, "manifest.json"))
        self.overlay = _read_json(os.path.join(data_dir, "semantic-overlay.json"))
        self.stopwords = set(fold(w) for w in self.overlay.get("stopwords_vi", []))

        self.nodes = {}
        self.by_type = defaultdict(list)
        for node_type, filename in CATALOG_FILES.items():
            records = _read_json(os.path.join(data_dir, "catalogs", filename))
            for record in records:
                record.setdefault("type", node_type)
                self.nodes[record["code"]] = record
                self.by_type[node_type].append(record)

        # Local enrichment: the published catalogs are too terse to combine well
        # (84/96 headline templates describe themselves in <=6 words, 38/44
        # formulas are bare acronyms, and mechanism/direction duplicate
        # description on every node). Merged under distinct keys so source data
        # stays byte-identical to the website.
        self.enrichment = {}
        enrich_dir = os.path.join(data_dir, "enrichment")
        if os.path.isdir(enrich_dir):
            for filename in sorted(os.listdir(enrich_dir)):
                if not filename.endswith(".json"):
                    continue
                block = _read_json(os.path.join(enrich_dir, filename))
                origin = block.get("_meta", {}).get("origin", "local-authored")
                for code, entry in block.items():
                    if code == "_meta" or not isinstance(entry, dict):
                        continue
                    merged = dict(entry)
                    merged["origin"] = origin
                    self.enrichment[code] = merged
        for code, entry in self.enrichment.items():
            node = self.nodes.get(code)
            if node is not None:
                node["ai_brief"] = entry.get("plain", "")
                node["when_to_use"] = entry.get("when", "")
                for extra in ("avoid", "risk", "feel", "deliver", "examples",
                              "master_question", "pillar_scope", "siblings"):
                    if entry.get(extra):
                        node[extra] = entry[extra]

        index = _read_json(os.path.join(data_dir, "graph-index.json"))
        self.graph_meta = index.get("meta", {})
        self.relations = {}
        for relation, adjacency in index.get("relations", {}).items():
            table = defaultdict(dict)
            for source, targets in adjacency.items():
                for target, weight in targets.items():
                    table[source][target] = weight
                    if relation in UNDIRECTED_RELATIONS:
                        table[target][source] = weight
            self.relations[relation] = table

        self.present_relations = [r for r in DECLARED_RELATIONS if self.relations.get(r)]
        self.missing_relations = [r for r in DECLARED_RELATIONS if not self.relations.get(r)]

        self.text_index = TextIndex(
            {code: self.node_text(node) for code, node in self.nodes.items()},
            self.stopwords,
        )

    # -- node helpers ------------------------------------------------------

    def node(self, code: str):
        return self.nodes.get(code)

    def label(self, code: str) -> str:
        node = self.nodes.get(code)
        return "%s %s" % (code, node["name"]) if node else code

    @staticmethod
    def node_text(node: dict) -> str:
        parts = [
            node.get("name", ""), node.get("description", ""),
            node.get("direction", ""), node.get("role", ""), node.get("scope", ""),
            node.get("mechanism", ""), node.get("template", ""),
            node.get("central_question", ""), node.get("approach", ""),
        ]
        structure = node.get("structure")
        if isinstance(structure, list):
            parts.extend(structure)
        parts.extend(node.get("tags", []) or [])
        return " ".join(p for p in parts if p)

    def tags(self, code: str) -> list:
        node = self.nodes.get(code)
        return list(node.get("tags", []) or []) if node else []

    def first_tag(self, code: str) -> str:
        tags = self.tags(code)
        return tags[0] if tags else ""

    def pillar_of(self, angle_code: str) -> str:
        node = self.nodes.get(angle_code)
        return node.get("parent_id", "") if node else ""

    def master_of(self, pillar_code: str) -> str:
        node = self.nodes.get(pillar_code)
        return node.get("parent_id", "") if node else ""

    def master_of_angle(self, angle_code: str) -> str:
        return self.master_of(self.pillar_of(angle_code))

    # -- graph helpers -----------------------------------------------------

    def weight(self, a: str, b: str, relation: str = "COMPATIBLE_WITH"):
        """Edge weight, or None when the edge does not exist."""
        table = self.relations.get(relation)
        if not table:
            return None
        return table.get(a, {}).get(b)

    def neighbors(self, code: str, node_type: str, relation: str = "COMPATIBLE_WITH") -> dict:
        table = self.relations.get(relation)
        if not table:
            return {}
        out = {}
        for target, weight in table.get(code, {}).items():
            node = self.nodes.get(target)
            if node and node.get("type") == node_type:
                out[target] = weight
        return out

    def positive_neighbors(self, code: str, node_type: str) -> dict:
        """Union over every positive relation that actually has edges.

        Keeps the engine forward compatible: when the site publishes
        RECOMMENDED_FOR / EXPRESSED_AS / DELIVERED_AS edges they are picked up
        without a code change, and the strongest relation wins per pair.
        """
        merged = {}
        for relation in POSITIVE_RELATIONS:
            for target, weight in self.neighbors(code, node_type, relation).items():
                if weight > merged.get(target, 0.0):
                    merged[target] = weight
        return merged

    def degree(self, code: str, relation: str = "COMPATIBLE_WITH") -> int:
        table = self.relations.get(relation) or {}
        return len(table.get(code, {}))

    # -- provenance --------------------------------------------------------

    def provenance(self) -> dict:
        return {
            "data_version": self.manifest.get("version"),
            "build_date": self.manifest.get("build_date"),
            "data_hash": self.manifest.get("data_hash"),
            "schema_version": self.manifest.get("schema_version"),
            "total_nodes": self.manifest.get("total_nodes"),
            "total_edges": self.manifest.get("total_edges"),
            "fetched_at": self.graph_meta.get("fetched_at"),
            "relations_present": self.present_relations,
            "relations_declared_but_empty": self.missing_relations,
            "semantic_overlay_origin": self.overlay.get("meta", {}).get("origin"),
        }


# --------------------------------------------------------------------------
# avoid rules (semantic fallback + real AVOID_WITH when it exists)
# --------------------------------------------------------------------------

def _selector_matches(data: MatrixData, selector: str, code: str) -> bool:
    if selector.startswith("code:"):
        return selector[5:] == code
    if selector.startswith("tag:"):
        _, node_type, tag = selector.split(":", 2)
        node = data.node(code)
        return bool(node) and node.get("type") == node_type and tag in (node.get("tags") or [])
    return selector == code


def avoid_conflicts(data: MatrixData, combo_codes: list, goal_codes: list) -> list:
    """Return conflicts for a combination, real edges first then overlay rules."""
    conflicts = []
    real = data.relations.get("AVOID_WITH")
    if real:
        for i, a in enumerate(combo_codes):
            for b in combo_codes[i + 1:]:
                weight = real.get(a, {}).get(b)
                if weight is not None:
                    conflicts.append({
                        "a": a, "b": b, "severity": "hard",
                        "reason": "Cạnh AVOID_WITH trong đồ thị (trọng số %.2f)" % weight,
                        "source": "graph",
                    })
    for rule in data.overlay.get("avoid_rules", []):
        for a in combo_codes:
            for b in combo_codes:
                if a == b:
                    continue
                if _selector_matches(data, rule["a"], a) and _selector_matches(data, rule["b"], b):
                    conflicts.append({
                        "a": a, "b": b, "severity": rule.get("severity", "soft"),
                        "reason": rule.get("reason", ""),
                        "source": "semantic_fallback",
                    })
    for rule in data.overlay.get("goal_ct_penalty", []):
        if rule["goal"] not in goal_codes:
            continue
        for code in combo_codes:
            node = data.node(code)
            if node and node.get("type") == "ContentType" and rule["ct_tag"] in (node.get("tags") or []):
                conflicts.append({
                    "a": rule["goal"], "b": code, "severity": "penalty",
                    "penalty": rule.get("penalty", 3),
                    "reason": rule.get("reason", ""),
                    "source": "semantic_fallback",
                })
    # de-duplicate on (a, b, reason)
    seen, unique = set(), []
    for conflict in conflicts:
        key = (conflict["a"], conflict["b"], conflict["reason"])
        if key not in seen:
            seen.add(key)
            unique.append(conflict)
    return unique
