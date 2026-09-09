#!/usr/bin/env python3
"""Refresh the offline MatrixContent snapshot from cm.auramarketers.com.

Read-only, GET only, same origin only, no API key, standard library only.

  python scripts/sync_matrixcontent.py --verify-only   # check for drift
  python scripts/sync_matrixcontent.py                 # fetch and rebuild
  python scripts/sync_matrixcontent.py --rebuild-index # rebuild index offline

Nothing is overwritten until every endpoint has been fetched and validated, so a
failed or corrupt download can never replace good local data.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matrix_lib import (  # noqa: E402
    CATALOG_FILES, DATA_DIR, DECLARED_RELATIONS, UNDIRECTED_RELATIONS,
)

ORIGIN = "https://cm.auramarketers.com"
MANIFEST_PATH = "/ai/manifest.json"
GRAPH_PATH = "/ai/graph.compact.json"
GRAPH_FULL_PATH = "/ai/graph.json"
USER_AGENT = "matrixcontent-creative-director/1.0 (+skill sync; GET only)"
TIMEOUT = 180

EXPECTED_TYPES = set(CATALOG_FILES)
CATALOG_PATH_TO_FILE = {
    "/ai/catalogs/master-pillars.json": "master-pillars.json",
    "/ai/catalogs/pillars.json": "pillars.json",
    "/ai/catalogs/content-angles.json": "content-angles.json",
    "/ai/catalogs/content-formulas.json": "content-formulas.json",
    "/ai/catalogs/success-patterns.json": "success-patterns.json",
    "/ai/catalogs/headline-templates.json": "headline-templates.json",
    "/ai/catalogs/content-types.json": "content-types.json",
    "/ai/catalogs/marketing-goals.json": "marketing-goals.json",
}
FILE_TO_TYPE = {v: k for k, v in CATALOG_FILES.items()}


class SyncError(RuntimeError):
    pass


def log(message: str) -> None:
    sys.stderr.write(message + "\n")


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------

def safe_url(path: str) -> str:
    """Join ORIGIN with a manifest-declared path, refusing anything off-origin."""
    url = urllib.parse.urljoin(ORIGIN, path)
    parsed = urllib.parse.urlparse(url)
    expected = urllib.parse.urlparse(ORIGIN)
    if parsed.scheme != "https" or parsed.netloc != expected.netloc:
        raise SyncError(
            "Từ chối endpoint khác origin: %s (chỉ chấp nhận %s)" % (url, ORIGIN)
        )
    return url


def fetch(path: str) -> bytes:
    url = safe_url(path)
    request = urllib.request.Request(url, method="GET", headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                raise SyncError("HTTP %s khi tải %s" % (response.status, url))
            return response.read()
    except urllib.error.HTTPError as exc:
        raise SyncError("HTTP %s khi tải %s — %s" % (exc.code, url, exc.reason))
    except urllib.error.URLError as exc:
        raise SyncError("Không kết nối được %s — %s" % (url, exc.reason))


def fetch_json(path: str):
    raw = fetch(path)
    try:
        return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SyncError("Nội dung tại %s không phải JSON hợp lệ — %s" % (path, exc))


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate_manifest(manifest: dict) -> None:
    for field in ("version", "build_date", "schema_version", "node_counts",
                  "total_nodes", "total_edges", "endpoints"):
        if field not in manifest:
            raise SyncError("Manifest thiếu trường bắt buộc: %s" % field)
    schema = str(manifest["schema_version"])
    if not schema.startswith("1."):
        raise SyncError(
            "Schema version %s chưa được hỗ trợ. Skill viết cho schema 1.x. "
            "Kiểm tra /ai/changelog.json rồi cập nhật scripts trước khi sync." % schema
        )
    missing_types = EXPECTED_TYPES - set(manifest["node_counts"])
    if missing_types:
        raise SyncError("Manifest thiếu node_counts cho: %s" % ", ".join(sorted(missing_types)))
    declared_total = sum(manifest["node_counts"].values())
    if declared_total != manifest["total_nodes"]:
        raise SyncError(
            "Manifest tự mâu thuẫn: tổng node_counts = %d nhưng total_nodes = %d"
            % (declared_total, manifest["total_nodes"])
        )


def validate_quality(quality: dict, force: bool) -> list:
    failed = [c for c in quality.get("checks", []) if not c.get("pass")]
    if failed and not force:
        lines = ["  - %s: kỳ vọng %s, thực tế %s" % (c.get("check"), c.get("expected"), c.get("actual"))
                 for c in failed]
        raise SyncError(
            "Data quality của nguồn đang FAIL, dừng để không ghi đè dữ liệu tốt:\n"
            + "\n".join(lines) + "\nDùng --force nếu vẫn muốn ghi."
        )
    return failed


def validate_catalog(filename: str, records, expected_count: int) -> None:
    node_type = FILE_TO_TYPE[filename]
    if not isinstance(records, list):
        raise SyncError("%s: kỳ vọng một mảng JSON" % filename)
    if len(records) != expected_count:
        raise SyncError(
            "%s: manifest công bố %d node nhưng tải về %d"
            % (filename, expected_count, len(records))
        )
    codes = set()
    for record in records:
        for field in ("id", "code", "name"):
            if not record.get(field):
                raise SyncError("%s: một bản ghi thiếu trường %s" % (filename, field))
        if record["code"] in codes:
            raise SyncError("%s: mã trùng lặp %s" % (filename, record["code"]))
        codes.add(record["code"])
        actual_type = record.get("type", node_type)
        if actual_type != node_type:
            raise SyncError(
                "%s: node %s có type=%s, kỳ vọng %s"
                % (filename, record["code"], actual_type, node_type)
            )


def validate_graph(graph, manifest: dict) -> dict:
    if not isinstance(graph, dict) or "nodes" not in graph or "edges" not in graph:
        raise SyncError("graph: kỳ vọng object có khóa 'nodes' và 'edges'")
    nodes, edges = graph["nodes"], graph["edges"]
    if len(nodes) != manifest["total_nodes"]:
        raise SyncError("graph: %d node, manifest công bố %d" % (len(nodes), manifest["total_nodes"]))
    if len(edges) != manifest["total_edges"]:
        raise SyncError("graph: %d cạnh, manifest công bố %d" % (len(edges), manifest["total_edges"]))
    known = {n.get("id") or n.get("code") for n in nodes}
    stats = {}
    for edge in edges:
        source = edge.get("source") or edge.get("s")
        target = edge.get("target") or edge.get("t")
        relation = edge.get("relation") or edge.get("r")
        if not source or not target or not relation:
            raise SyncError("graph: cạnh thiếu source/target/relation — %r" % (edge,))
        if source not in known or target not in known:
            raise SyncError("graph: cạnh trỏ tới node không tồn tại — %s -> %s" % (source, target))
        stats[relation] = stats.get(relation, 0) + 1
    unknown = set(stats) - set(DECLARED_RELATIONS)
    if unknown:
        log("  ! Quan hệ ngoài từ vựng công bố (vẫn nạp): %s" % ", ".join(sorted(unknown)))
    return stats


# --------------------------------------------------------------------------
# index building
# --------------------------------------------------------------------------

def build_index(graph, manifest: dict, stats: dict, hashes: dict, source_path: str) -> dict:
    relations = {}
    for edge in graph["edges"]:
        source = edge.get("source") or edge.get("s")
        target = edge.get("target") or edge.get("t")
        relation = edge.get("relation") or edge.get("r")
        weight = edge.get("weight", edge.get("w", 1))
        table = relations.setdefault(relation, {})
        bucket = table.setdefault(source, {})
        # keep the strongest weight if the source publishes duplicates
        if weight > bucket.get(target, -1):
            bucket[target] = round(float(weight), 4)

    present = [r for r in DECLARED_RELATIONS if stats.get(r)]
    missing = [r for r in DECLARED_RELATIONS if not stats.get(r)]
    return {
        "meta": {
            "built_by": "sync_matrixcontent.py",
            "fetched_at": datetime.datetime.now(datetime.timezone.utc)
                          .replace(microsecond=0).isoformat(),
            "origin": ORIGIN,
            "graph_source": source_path,
            "data_version": manifest.get("version"),
            "build_date": manifest.get("build_date"),
            "data_hash": manifest.get("data_hash"),
            "schema_version": manifest.get("schema_version"),
            "total_nodes": manifest.get("total_nodes"),
            "total_edges": manifest.get("total_edges"),
            "source_sha256": hashes,
            "undirected_relations": sorted(UNDIRECTED_RELATIONS),
            "relations_present": present,
            "relations_declared_but_empty": missing,
            "note": ("Adjacency chỉ lưu theo chiều gốc của cạnh; matrix_lib nạp "
                     "chiều ngược cho các quan hệ vô hướng."),
        },
        "relation_stats": stats,
        "relations": relations,
    }


def write_json(path: str, payload) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def load_local_manifest():
    path = os.path.join(DATA_DIR, "manifest.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def verify_only() -> int:
    local = load_local_manifest()
    remote, _ = fetch_json(MANIFEST_PATH)
    validate_manifest(remote)
    quality, _ = fetch_json("/ai/data-quality.json")
    failed = [c for c in quality.get("checks", []) if not c.get("pass")]

    log("Nguồn : v%s · build %s · hash %s · %s node / %s cạnh" % (
        remote.get("version"), remote.get("build_date"), remote.get("data_hash"),
        remote.get("total_nodes"), remote.get("total_edges")))
    if local:
        log("Cục bộ: v%s · build %s · hash %s · %s node / %s cạnh" % (
            local.get("version"), local.get("build_date"), local.get("data_hash"),
            local.get("total_nodes"), local.get("total_edges")))
    else:
        log("Cục bộ: chưa có snapshot")

    if failed:
        log("! Data quality nguồn đang FAIL ở %d mục" % len(failed))

    drift = (not local) or any(
        local.get(k) != remote.get(k)
        for k in ("version", "build_date", "data_hash", "total_nodes", "total_edges")
    )
    if drift:
        log("=> Dữ liệu đã thay đổi. Chạy: python scripts/sync_matrixcontent.py")
        return 2
    log("=> Snapshot cục bộ khớp nguồn.")
    return 0


def rebuild_index_only(graph_file: str) -> int:
    manifest = load_local_manifest()
    if manifest is None:
        raise SyncError("Chưa có data/manifest.json cục bộ để rebuild.")
    with open(graph_file, "rb") as handle:
        raw = handle.read()
    graph = json.loads(raw.decode("utf-8"))
    stats = validate_graph(graph, manifest)
    index = build_index(graph, manifest, stats,
                        {"graph": hashlib.sha256(raw).hexdigest()}, graph_file)
    write_json(os.path.join(DATA_DIR, "graph-index.json"), index)
    log("Đã dựng lại graph-index.json từ %s" % graph_file)
    log("  quan hệ có cạnh: %s" % ", ".join(index["meta"]["relations_present"]))
    return 0


def sync(force: bool, keep_graph: bool) -> int:
    log("1/5 Tải manifest…")
    manifest, manifest_hash = fetch_json(MANIFEST_PATH)
    validate_manifest(manifest)
    log("    v%s · build %s · %s node / %s cạnh" % (
        manifest["version"], manifest["build_date"],
        manifest["total_nodes"], manifest["total_edges"]))

    log("2/5 Kiểm tra data quality…")
    quality, quality_hash = fetch_json("/ai/data-quality.json")
    failed = validate_quality(quality, force)
    if failed:
        log("    ! Bỏ qua %d mục FAIL do --force" % len(failed))
    else:
        log("    Toàn bộ kiểm tra PASS")

    declared = {e["path"] for e in manifest.get("endpoints", []) if isinstance(e, dict)}
    hashes = {MANIFEST_PATH: manifest_hash, "/ai/data-quality.json": quality_hash}

    log("3/5 Tải catalogs…")
    catalogs = {}
    for path, filename in CATALOG_PATH_TO_FILE.items():
        if path not in declared:
            raise SyncError(
                "Manifest không còn công bố %s. Cấu trúc nguồn đã đổi — "
                "kiểm tra /ai/changelog.json trước khi ép sync." % path
            )
        records, digest = fetch_json(path)
        node_type = FILE_TO_TYPE[filename]
        validate_catalog(filename, records, manifest["node_counts"][node_type])
        catalogs[filename] = records
        hashes[path] = digest
        log("    %-28s %4d node  ok" % (filename, len(records)))

    changelog = None
    if "/ai/changelog.json" in declared:
        changelog, hashes["/ai/changelog.json"] = fetch_json("/ai/changelog.json")

    log("4/5 Tải đồ thị…")
    graph_path = GRAPH_PATH if GRAPH_PATH in declared else GRAPH_FULL_PATH
    graph, graph_hash = fetch_json(graph_path)
    hashes[graph_path] = graph_hash
    stats = validate_graph(graph, manifest)
    log("    %s · %s" % (graph_path, " · ".join("%s %d" % kv for kv in sorted(stats.items()))))

    log("5/5 Ghi dữ liệu…")
    staging = tempfile.mkdtemp(prefix="matrixcontent-sync-")
    try:
        write_json(os.path.join(staging, "manifest.json"), manifest)
        write_json(os.path.join(staging, "data-quality.json"), quality)
        if changelog is not None:
            write_json(os.path.join(staging, "changelog.json"), changelog)
        for filename, records in catalogs.items():
            write_json(os.path.join(staging, "catalogs", filename), records)
        write_json(os.path.join(staging, "graph-index.json"),
                   build_index(graph, manifest, stats, hashes, graph_path))
        if keep_graph:
            write_json(os.path.join(staging, "graph.compact.json"), graph)

        os.makedirs(os.path.join(DATA_DIR, "catalogs"), exist_ok=True)
        for root, _dirs, files in os.walk(staging):
            for name in files:
                source = os.path.join(root, name)
                target = os.path.join(DATA_DIR, os.path.relpath(source, staging))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.move(source, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    log("Xong. data/ đang ở v%s (build %s, hash %s)."
        % (manifest["version"], manifest["build_date"], manifest.get("data_hash")))
    empty = [r for r in DECLARED_RELATIONS if not stats.get(r)]
    if empty:
        log("Lưu ý: %d quan hệ được khai báo nhưng không có cạnh: %s"
            % (len(empty), ", ".join(empty)))
        log("       Các tín hiệu tương ứng vẫn đến từ semantic-overlay.json.")
    log("Cập nhật references/source-provenance.md nếu phiên bản đã đổi.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verify-only", action="store_true",
                        help="chỉ so sánh phiên bản nguồn với snapshot cục bộ")
    parser.add_argument("--force", action="store_true",
                        help="vẫn ghi dù data quality nguồn FAIL")
    parser.add_argument("--keep-graph", action="store_true",
                        help="giữ cả bản graph.compact.json thô (~7MB)")
    parser.add_argument("--rebuild-index", metavar="GRAPH_FILE",
                        help="dựng lại graph-index.json từ file đồ thị có sẵn, không cần mạng")
    args = parser.parse_args()

    try:
        if args.rebuild_index:
            return rebuild_index_only(args.rebuild_index)
        if args.verify_only:
            return verify_only()
        return sync(args.force, args.keep_graph)
    except SyncError as exc:
        log("LỖI: %s" % exc)
        return 1
    except KeyboardInterrupt:
        log("Đã hủy.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
