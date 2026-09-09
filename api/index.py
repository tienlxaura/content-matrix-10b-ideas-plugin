"""Content Matrix 10B Ideas - Serverless API & OpenAI Plugin Backend.

Deployed on Vercel to power:
1. OpenAI Agent Plugins
2. ChatGPT Custom GPT Actions
3. Interactive Web Tester & API Playground
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field

# Ensure script paths are accessible
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(CURRENT_DIR)
SKILL_DIR = os.path.join(PLUGIN_ROOT, "skills", "content-matrix")
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
DATA_DIR = os.path.join(SKILL_DIR, "data")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

os.environ["CONTENT_MATRIX_DATA_DIR"] = DATA_DIR

try:
    import matrix_lib
    import select_combinations
    matrix_data = matrix_lib.MatrixData()
except Exception as e:
    print(f"Warning: Failed to load MatrixData at startup: {e}", file=sys.stderr)
    matrix_data = None

app = FastAPI(
    title="Content Matrix 10B Ideas API",
    description="Universal Content Engine & Creative Director powered by 991 nodes and 69,720 edges.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Enable CORS for ChatGPT and all web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------

class BriefInput(BaseModel):
    topic: str = Field(..., description="Chủ đề nội dung hoặc bài viết (Bắt buộc)", example="Quảng cáo khoá học UCMAS")
    brand: Optional[str] = Field("", description="Tên thương hiệu", example="UCMAS Việt Nam")
    industry: Optional[str] = Field("", description="Ngành hàng", example="Giáo dục tư duy trẻ em")
    product: Optional[str] = Field("", description="Sản phẩm / Dịch vụ", example="Khoá học bàn tính số học")
    audience: Optional[str] = Field("", description="Khách hàng mục tiêu", example="Phụ huynh có con 4-10 tuổi")
    insight: Optional[str] = Field("", description="Sự thật ngầm hiểu", example="Phụ huynh sợ con nghiện điện thoại, thiếu tập trung")
    marketing_goal: Optional[str] = Field("", description="Mục tiêu marketing", example="Khách nhắn tin tư vấn")
    goal_codes: Optional[List[str]] = Field(default_factory=list, description="Mã mục tiêu (RC01..RC24)")
    journey_stage: Optional[str] = Field("awareness", description="awareness, consideration, decision, retention, advocacy")
    awareness_stage: Optional[str] = Field("problem", description="unaware, problem, solution, product, most_aware")
    channels: Optional[List[str]] = Field(default_factory=lambda: ["facebook", "tiktok"])
    count: Optional[int] = Field(10, ge=1, le=20, description="Số lượng tổ hợp 5 điểm cần trả về")
    diversity: Optional[float] = Field(0.35, ge=0.0, le=1.0, description="Độ đa dạng giữa các tổ hợp")
    seed: Optional[int] = Field(0, description="Hạt ngẫu nhiên")
    explain: Optional[bool] = Field(False, description="Kèm giải thích trọng số đồ thị")


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@app.get("/health")
def health():
    if not matrix_data:
        raise HTTPException(status_code=503, detail="MatrixData graph not loaded")
    return {
        "status": "healthy",
        "engine": "Content Matrix 10.000.000.000 Idea",
        "nodes": len(matrix_data.nodes),
        "edges": matrix_data.graph_meta.get("total_edges", 69720),
        "version": "1.0.0",
        "author": "Aura Marketers",
    }


@app.get("/plugin.json")
def get_plugin_manifest(request: Request):
    manifest_path = os.path.join(PLUGIN_ROOT, "plugin.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    return {"error": "plugin.json not found"}


@app.get("/.well-known/ai-plugin.json")
def get_ai_plugin_manifest(request: Request):
    path = os.path.join(PLUGIN_ROOT, ".well-known", "ai-plugin.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Update server URL dynamically
        host = str(request.base_url).rstrip("/")
        data["api"]["url"] = f"{host}/openapi.json"
        data["logo_url"] = f"{host}/assets/logo.png"
        return data
    return {"error": "ai-plugin.json not found"}


@app.get("/mcp.json")
def get_mcp_config():
    path = os.path.join(PLUGIN_ROOT, "mcp.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "mcp.json not found"}


@app.get("/assets/{filename}")
def get_asset(filename: str):
    asset_path = os.path.join(PLUGIN_ROOT, "assets", filename)
    if os.path.exists(asset_path):
        media_type = "image/png" if filename.endswith(".png") else "application/octet-stream"
        return FileResponse(asset_path, media_type=media_type)
    raise HTTPException(status_code=404, detail="Asset not found")


@app.post("/api/select")
def select_combinations_endpoint(payload: BriefInput):
    global matrix_data
    if not matrix_data:
        try:
            matrix_data = matrix_lib.MatrixData()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load graph: {e}")

    try:
        raw_brief = payload.model_dump()
        result = select_combinations.run(
            matrix_data,
            raw_brief,
            count=payload.count,
            diversity=payload.diversity,
            seed=payload.seed,
            explain=payload.explain,
            pool_size=max(30, payload.count * 3)
        )
        return result
    except matrix_lib.DataError as de:
        raise HTTPException(status_code=400, detail=str(de))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}")


@app.get("/api/catalogs")
def get_catalogs(type: str = Query("all", description="MasterPillar, Pillar, ContentAngle, ContentFormula, SuccessPattern, HeadlineTemplate, ContentType, MarketingGoal"), search: Optional[str] = None):
    global matrix_data
    if not matrix_data:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    items = []
    types_to_fetch = [type] if type != "all" else list(matrix_lib.CATALOG_FILES.keys())

    for cat_type in types_to_fetch:
        nodes = matrix_data.by_type.get(cat_type, [])
        for node in nodes:
            node_id = node.get("code") or node.get("id") or ""
            label = node.get("name") or node.get("description") or node_id
            if search and search.lower() not in (node_id.lower() + " " + label.lower()):
                continue
            items.append({
                "id": node_id,
                "type": cat_type,
                "label": label,
                "description": node.get("description", ""),
            })

    return {
        "count": len(items),
        "catalog_type": type,
        "items": items[:100],  # limit to top 100
    }


@app.post("/api/validate")
def validate_combination_endpoint(payload: Dict[str, Any]):
    global matrix_data
    if not matrix_data:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    
    # Check if combination has angle, formula, pattern, headline, type
    combo = payload.get("combination", payload)
    codes = [combo.get(k, {}).get("code") or combo.get(k) for k in ("angle", "formula", "pattern", "headline", "type")]
    valid_codes = [c for c in codes if c and c in matrix_data.nodes]
    
    conflicts = []
    # Check pairwise conflicts
    for i in range(len(valid_codes)):
        for j in range(i + 1, len(valid_codes)):
            c1, c2 = valid_codes[i], valid_codes[j]
            weight = matrix_data.weight(c1, c2)
            if weight < 0.40:
                conflicts.append({"pair": [c1, c2], "weight": weight, "note": "Low affinity or conflict"})

    return {
        "is_valid": len(conflicts) == 0,
        "checked_nodes": valid_codes,
        "conflicts": conflicts
    }


# --------------------------------------------------------------------------
# Interactive Web Dashboard & Playground
# --------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Matrix 10B Ideas — OpenAI Agent Plugin & API</title>
    <link rel="icon" type="image/png" href="/assets/icon.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #080B11;
            --bg-card: rgba(17, 24, 39, 0.7);
            --bg-card-hover: rgba(30, 41, 59, 0.8);
            --border-subtle: rgba(255, 107, 0, 0.15);
            --border-glow: rgba(255, 107, 0, 0.4);
            --primary: #FF6B00;
            --primary-glow: #FF8833;
            --accent-blue: #38BDF8;
            --accent-green: #34D399;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --font-sans: 'Plus Jakarta Sans', system-ui, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-base);
            color: var(--text-main);
            font-family: var(--font-sans);
            min-height: 100vh;
            line-height: 1.6;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(255, 107, 0, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 85% 75%, rgba(56, 189, 248, 0.08) 0%, transparent 40%);
        }

        .container { max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }

        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            margin-bottom: 2.5rem;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .brand { display: flex; align-items: center; gap: 1rem; }
        .brand img { width: 50px; height: 50px; border-radius: 12px; box-shadow: 0 0 20px rgba(255, 107, 0, 0.4); }
        .brand h1 { font-size: 1.5rem; font-weight: 800; letter-spacing: -0.02em; }
        .brand span { color: var(--primary); }

        .badges { display: flex; gap: 0.5rem; align-items: center; }
        .badge {
            font-size: 0.75rem;
            padding: 0.25rem 0.65rem;
            border-radius: 999px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }
        .badge-primary {
            background: rgba(255, 107, 0, 0.15);
            border-color: var(--border-glow);
            color: var(--primary-glow);
        }
        .badge-green {
            background: rgba(52, 211, 153, 0.15);
            border-color: rgba(52, 211, 153, 0.3);
            color: var(--accent-green);
        }

        .hero {
            text-align: center;
            padding: 2rem 0 3.5rem;
        }
        .hero h2 {
            font-size: 2.75rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #FFF 40%, var(--primary-glow) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero p {
            color: var(--text-muted);
            font-size: 1.15rem;
            max-width: 720px;
            margin: 0 auto 2rem;
        }

        .action-links {
            display: flex;
            justify-content: center;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border-radius: 10px;
            font-size: 0.95rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--primary) 0%, #E05300 100%);
            color: white;
            box-shadow: 0 4px 20px rgba(255, 107, 0, 0.35);
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 25px rgba(255, 107, 0, 0.5);
        }
        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.25);
        }

        /* Playground Layout */
        .playground-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 4rem;
        }
        @media (max-width: 960px) {
            .playground-grid { grid-template-columns: 1fr; }
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        .card-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .form-group { margin-bottom: 1.2rem; }
        .form-label {
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 0.4rem;
            color: var(--text-muted);
        }
        .form-control {
            width: 100%;
            padding: 0.75rem 1rem;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            color: white;
            font-family: inherit;
            font-size: 0.95rem;
            transition: border-color 0.2s;
        }
        .form-control:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(255, 107, 0, 0.15);
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }

        .presets {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }
        .preset-btn {
            font-size: 0.75rem;
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.15s;
        }
        .preset-btn:hover {
            color: white;
            border-color: var(--primary);
            background: rgba(255, 107, 0, 0.1);
        }

        .results-container {
            max-height: 540px;
            overflow-y: auto;
            padding-right: 0.5rem;
        }
        .result-item {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            transition: transform 0.2s, border-color 0.2s;
        }
        .result-item:hover {
            border-color: var(--border-glow);
            transform: translateY(-2px);
        }
        .result-rank {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            border-radius: 8px;
            background: var(--primary);
            color: white;
            font-weight: 700;
            font-size: 0.85rem;
            margin-bottom: 0.75rem;
        }
        .result-score {
            float: right;
            font-family: var(--font-mono);
            font-size: 0.85rem;
            color: var(--accent-green);
            background: rgba(52, 211, 153, 0.1);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
        }
        .point-tag {
            display: inline-block;
            font-size: 0.75rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            margin: 0.2rem 0.2rem 0.2rem 0;
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .hook-box {
            margin-top: 0.75rem;
            padding: 0.75rem;
            background: rgba(0, 0, 0, 0.3);
            border-left: 3px solid var(--primary);
            border-radius: 0 6px 6px 0;
            font-size: 0.88rem;
            color: #E2E8F0;
        }

        /* Installation Guide Section */
        .guide-section {
            margin-top: 3rem;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            padding-top: 3rem;
        }
        .guide-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }
        .guide-card {
            background: var(--bg-card);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 1.5rem;
        }
        .guide-card h3 {
            font-size: 1.15rem;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .code-box {
            background: #020617;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-family: var(--font-mono);
            font-size: 0.8rem;
            color: #38BDF8;
            margin-top: 0.75rem;
            overflow-x: auto;
            position: relative;
        }

        footer {
            text-align: center;
            padding: 3rem 0;
            color: var(--text-muted);
            font-size: 0.9rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            margin-top: 4rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <img src="/assets/logo.png" alt="Aura Logo">
                <div>
                    <h1>Content Matrix <span>10B</span></h1>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">Universal Content Engine & Creative Director</div>
                </div>
            </div>
            <div class="badges">
                <span class="badge badge-green">● 991 Nodes / 69,720 Edges Live</span>
                <span class="badge badge-primary">OpenAI Agent Plugin Ready</span>
                <span class="badge">GPT Action Ready</span>
            </div>
        </header>

        <section class="hero">
            <h2>Ý Tưởng Triệu View Nối Liền 5 Điểm Chiến Lược</h2>
            <p>Vận hành trên đồ thị tri thức MatrixContent. Biến brief sơ sài thành các hướng ý tưởng sắc bén, kịch bản chuyển đổi cao và câu chữ chân thực mà không có văn mẫu AI sáo rỗng.</p>
            <div class="action-links">
                <a href="#playground" class="btn btn-primary">⚡ Dùng thử Interactive Tester</a>
                <a href="/docs" target="_blank" class="btn btn-secondary">📖 API Swagger Docs</a>
                <a href="/openapi.json" target="_blank" class="btn btn-secondary">⚙️ OpenAPI Spec</a>
                <a href="/plugin.json" target="_blank" class="btn btn-secondary">🧩 plugin.json</a>
            </div>
        </section>

        <section id="playground" class="playground-grid">
            <!-- Left: Form Brief -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📝 Nhập Brief Tiếp Thị</div>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">JSON Engine v2.0</span>
                </div>

                <div class="presets">
                    <span style="font-size: 0.75rem; color: var(--text-muted); align-self: center;">Mẫu nhanh:</span>
                    <button class="preset-btn" onclick="loadPreset('ucmas')">Toán UCMAS</button>
                    <button class="preset-btn" onclick="loadPreset('saas')">SaaS AI Agent</button>
                    <button class="preset-btn" onclick="loadPreset('coffee')">Quán Cà Phê</button>
                </div>

                <form id="briefForm" onsubmit="event.preventDefault(); runEngine();">
                    <div class="form-group">
                        <label class="form-label">Chủ đề chính (Topic) *</label>
                        <input type="text" id="topic" class="form-control" required placeholder="Quảng cáo khoá học toán tư duy UCMAS">
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">Thương hiệu (Brand)</label>
                            <input type="text" id="brand" class="form-control" placeholder="UCMAS Việt Nam">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Ngành hàng (Industry)</label>
                            <input type="text" id="industry" class="form-control" placeholder="Giáo dục trẻ em">
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Đối tượng mục tiêu (Audience)</label>
                        <input type="text" id="audience" class="form-control" placeholder="Phụ huynh có con 4-10 tuổi thiếu tập trung">
                    </div>

                    <div class="form-group">
                        <label class="form-label">Insight khách hàng (Insight)</label>
                        <input type="text" id="insight" class="form-control" placeholder="Phụ huynh sợ con nghiện điện thoại, muốn con bứt phá tư duy">
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-label">Mục tiêu (Marketing Goal)</label>
                            <input type="text" id="marketing_goal" class="form-control" placeholder="Khách inbox đăng ký học thử">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Số hướng (Count: 1-10)</label>
                            <input type="number" id="count" class="form-control" value="3" min="1" max="10">
                        </div>
                    </div>

                    <button type="submit" id="submitBtn" class="btn btn-primary" style="width: 100%; justify-content: center; margin-top: 1rem;">
                        ✨ Tính toán 5 Điểm Ngay
                    </button>
                </form>
            </div>

            <!-- Right: Results -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">💡 Top Tổ Hợp Đề Xuất</div>
                    <span id="timingBadge" style="font-size: 0.75rem; color: var(--accent-green);"></span>
                </div>

                <div id="resultsContainer" class="results-container">
                    <div style="text-align: center; color: var(--text-muted); padding: 4rem 1rem;">
                        <p>Nhập brief bên trái hoặc chọn một mẫu nhanh rồi bấm <strong>"Tính toán 5 Điểm"</strong> để xem kết quả trực tiếp từ Knowledge Graph.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Installation Section -->
        <section class="guide-section">
            <h2 style="font-size: 1.8rem; font-weight: 800; text-align: center; margin-bottom: 0.5rem;">Cài Đặt & Sử Dụng Trên ChatGPT</h2>
            <p style="text-align: center; color: var(--text-muted); max-width: 600px; margin: 0 auto;">Dễ dàng tích hợp vào ChatGPT theo 2 cách tùy thuộc nền tảng bạn sử dụng:</p>

            <div class="guide-grid">
                <div class="guide-card">
                    <h3>🖥️ 1. ChatGPT Desktop & Codex</h3>
                    <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.75rem;">Cài đặt plugin nội bộ từ repo marketplace hoặc qua Codex CLI:</p>
                    <div class="code-box">codex plugin marketplace add tienlxaura/content-matrix-10b-ideas-plugin</div>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.75rem;">Hoặc vào <strong>ChatGPT Settings &gt; Plugins</strong>, chọn Local Marketplace và bật <strong>Content Matrix 10B Ideas</strong>.</p>
                </div>

                <div class="guide-card">
                    <h3>🌐 2. ChatGPT Web (Custom GPT Actions)</h3>
                    <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.75rem;">Tạo Custom GPT trên <a href="https://chatgpt.com/gpts/editor" target="_blank" style="color: var(--primary);">chatgpt.com/create</a>:</p>
                    <ul style="font-size: 0.85rem; color: var(--text-muted); padding-left: 1.2rem; line-height: 1.8;">
                        <li>Vào tab <strong>Configure</strong> &gt; <strong>Actions</strong> &gt; <strong>Create new action</strong>.</li>
                        <li>Bấm <strong>Import from URL</strong> và dán:</li>
                    </ul>
                    <div class="code-box" id="openapiUrlBox">https://content-matrix-10b-ideas.vercel.app/openapi.json</div>
                    <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.75rem;">ChatGPT sẽ tự động nhận diện các Action: <code>selectMatrixCombinations</code>, <code>getCatalogNodes</code>, <code>validateCombination</code>.</p>
                </div>
            </div>
        </section>

        <footer>
            <p>© 2026 Aura Marketers. All rights reserved. Powered by MatrixContent Knowledge Graph.</p>
        </footer>
    </div>

    <script>
        // Update URL based on current host
        const currentHost = window.location.origin;
        document.getElementById('openapiUrlBox').innerText = `${currentHost}/openapi.json`;

        const presets = {
            ucmas: {
                topic: "Quảng cáo khoá học toán tư duy UCMAS cho trẻ",
                brand: "UCMAS Việt Nam",
                industry: "Giáo dục tư duy trẻ em",
                audience: "Phụ huynh có con 4-10 tuổi lo lắng con thiếu tập trung",
                insight: "Phụ huynh sợ con nghiện màn hình, mất tập trung nhưng không biết phương pháp rèn luyện trí não",
                marketing_goal: "Khách nhắn tin fanpage để nhận tư vấn học thử",
                count: 3
            },
            saas: {
                topic: "Phần mềm AI agent tự động hoá quy trình cho doanh nghiệp",
                brand: "Aura Agent Platform",
                industry: "SaaS AI B2B",
                audience: "Giám đốc vận hành (COO), Trưởng phòng IT",
                insight: "Đã thử nhiều AI nhưng vẫn tắc ở khâu phê duyệt và kiểm soát audit log",
                marketing_goal: "Đặt lịch demo giải pháp 1-1",
                count: 3
            },
            coffee: {
                topic: "Chiến dịch ra mắt bộ sưu tập cà phê ủ lạnh Cold Brew thảo mộc",
                brand: "Aura Artisan Coffee",
                industry: "F&B Đồ uống cao cấp",
                audience: "Dân văn phòng, người làm việc sáng tạo cần sự tỉnh táo kéo dài",
                insight: "Muốn uống cà phê đậm vị nhưng sợ ép tim, cồn cào ruột khi uống lúc đói",
                marketing_goal: "Tăng lượng khách đến trải nghiệm tại quán cuối tuần",
                count: 3
            }
        };

        function loadPreset(key) {
            const p = presets[key];
            if (!p) return;
            document.getElementById('topic').value = p.topic;
            document.getElementById('brand').value = p.brand;
            document.getElementById('industry').value = p.industry;
            document.getElementById('audience').value = p.audience;
            document.getElementById('insight').value = p.insight;
            document.getElementById('marketing_goal').value = p.marketing_goal;
            document.getElementById('count').value = p.count;
            runEngine();
        }

        async function runEngine() {
            const btn = document.getElementById('submitBtn');
            const results = document.getElementById('resultsContainer');
            const timing = document.getElementById('timingBadge');

            const payload = {
                topic: document.getElementById('topic').value,
                brand: document.getElementById('brand').value,
                industry: document.getElementById('industry').value,
                audience: document.getElementById('audience').value,
                insight: document.getElementById('insight').value,
                marketing_goal: document.getElementById('marketing_goal').value,
                count: parseInt(document.getElementById('count').value) || 3
            };

            btn.disabled = true;
            btn.innerText = "⏳ Đang tính toán trên đồ thị...";
            timing.innerText = "";
            results.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 3rem;">Đang quét 991 nodes và 69.720 edges...</div>`;

            const startTime = performance.now();

            try {
                const res = await fetch('/api/select', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                const duration = ((performance.now() - startTime) / 1000).toFixed(2);

                if (!res.ok) {
                    throw new Error(data.detail || "Lỗi xử lý");
                }

                timing.innerText = `Hoàn tất trong ${duration}s`;

                if (!data.combinations || data.combinations.length === 0) {
                    results.innerHTML = `<p style="color: #F87171;">Không tìm thấy tổ hợp phù hợp.</p>`;
                    return;
                }

                results.innerHTML = data.combinations.map(item => {
                    const fp = item.five_points || {};
                    const angle = fp.content_angle || {};
                    const formula = fp.content_formula || {};
                    const pattern = fp.success_pattern || {};
                    const headline = fp.headline_template || {};
                    const ctype = fp.content_type || {};
                    const sample = (headline.examples && headline.examples[0]) || headline.template || (angle.name + ' — Đột phá mới');

                    return `
                    <div class="result-item">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <span class="result-rank">#${item.rank}</span>
                            <span class="result-score">Điểm: ${item.score ? item.score.toFixed(1) : '95'} | ${item.selection_mechanism || 'brief'}</span>
                        </div>
                        <div style="margin-bottom: 0.6rem;">
                            <span class="point-tag" style="background: rgba(255, 107, 0, 0.2); border-color: var(--primary);">🎯 Angle: <strong>${angle.name || ''}</strong> (${angle.code || ''})</span>
                            <span class="point-tag" style="background: rgba(255, 145, 0, 0.2);">📐 Formula: <strong>${formula.name || ''}</strong> (${formula.code || ''})</span>
                            <span class="point-tag" style="background: rgba(255, 75, 43, 0.2);">⚡ Pattern: <strong>${pattern.name || ''}</strong> (${pattern.code || ''})</span>
                            <span class="point-tag" style="background: rgba(255, 180, 0, 0.2);">🏷️ Headline: <strong>${headline.name || ''}</strong> (${headline.code || ''})</span>
                            <span class="point-tag" style="background: rgba(56, 189, 248, 0.2);">📱 Type: <strong>${ctype.name || ''}</strong> (${ctype.code || ''})</span>
                        </div>
                        <div class="hook-box">
                            <div style="color: var(--primary-glow); font-weight: 700; margin-bottom: 0.2rem;">💡 Mẫu tiêu đề đề xuất:</div>
                            <div style="font-weight: 500; font-size: 0.92rem;">${sample}</div>
                            <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.35rem;"><strong>Cấu trúc:</strong> ${formula.description || ''} | <strong>Chiến thuật:</strong> ${pattern.mechanism || pattern.description || ''}</div>
                        </div>
                    </div>
                    `;
                }).join('');

            } catch (err) {
                results.innerHTML = `<div style="color: #F87171; padding: 1rem; background: rgba(239, 68, 68, 0.1); border-radius: 8px;">Lỗi: ${err.message}</div>`;
            } finally {
                btn.disabled = false;
                btn.innerText = "✨ Tính toán 5 Điểm Ngay";
            }
        }
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
