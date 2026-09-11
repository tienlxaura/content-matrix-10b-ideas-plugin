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

# Vercel Internal Rewrite Path Normalization
@app.middleware("http")
async def normalize_vercel_path(request: Request, call_next):
    # Check both request path and Vercel routing headers
    matched = request.headers.get("x-matched-path") or request.headers.get("x-vercel-matched-path") or ""
    path = request.scope.get("path", "")
    
    target = path
    if matched and ("/api/index.py" in matched or "/api/index" in matched):
        target = matched

    for prefix in ("/api/index.py", "/api/index"):
        if target.startswith(prefix):
            cleaned = target[len(prefix):]
            request.scope["path"] = cleaned if (cleaned and cleaned.startswith("/")) else ("/" + cleaned if cleaned else "/")
            break

    response = await call_next(request)
    return response


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
    count: Optional[int] = Field(10, ge=1, le=50, description="Số lượng tổ hợp 5 điểm cần trả về")
    diversity: Optional[float] = Field(0.35, ge=0.0, le=1.0, description="Độ đa dạng giữa các tổ hợp")
    seed: Optional[int] = Field(0, description="Hạt ngẫu nhiên")
    explain: Optional[bool] = Field(False, description="Kèm giải thích trọng số đồ thị")
    mode: Optional[str] = Field("default", description="Chế độ sáng tạo: default (mặc định), research (nghiên cứu công thức, cấm demo), deep (chuyên sâu N*100)")
    target_count: Optional[int] = Field(3, ge=1, le=10, description="Số ý tưởng mong muốn nhận ở chế độ chuyên sâu (N)")
    multiplier: Optional[int] = Field(100, ge=10, le=200, description="Hệ số nhân ứng viên trích xuất ở chế độ chuyên sâu (mặc định 100)")


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


# --------------------------------------------------------------------------
# MCP Streamable HTTP Server Endpoint (Model Context Protocol)
# Compatible with ChatGPT Developer Mode / With MCP
# --------------------------------------------------------------------------

@app.api_route("/mcp", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/api/mcp", methods=["GET", "POST", "OPTIONS"])
async def mcp_streamable_http_handler(request: Request):
    """MCP Streamable HTTP protocol endpoint for ChatGPT Developer Mode."""
    if request.method == "OPTIONS":
        return Response(status_code=200)

    if request.method == "GET":
        # Check if client requested SSE
        accept = request.headers.get("accept", "")
        if "text/event-stream" in accept:
            async def sse_stream():
                yield "event: endpoint\ndata: /mcp\n\n"
            from fastapi.responses import StreamingResponse
            return StreamingResponse(sse_stream(), media_type="text/event-stream")
        return JSONResponse({
            "status": "active",
            "protocol": "mcp",
            "transport": "streamable-http",
            "server": "Content Matrix 10B Ideas MCP Server",
            "version": "1.1.0",
            "capabilities": ["tools", "prompts", "resources"],
            "url": "https://content-matrix-10b-ideas-plugin.vercel.app/mcp"
        })

    # Handle POST JSON-RPC 2.0 requests
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Invalid JSON"}}, status_code=400)

    method = body.get("method")
    req_id = body.get("id")
    params = body.get("params", {}) or {}

    global matrix_data
    if not matrix_data:
        try:
            matrix_data = matrix_lib.MatrixData()
        except Exception as e:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": f"Graph load error: {str(e)}"}
            }, status_code=500)

    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    },
                    "prompts": {
                        "listChanged": False
                    },
                    "resources": {
                        "subscribe": False,
                        "listChanged": False
                    }
                },
                "serverInfo": {
                    "name": "content-matrix-10b-ideas",
                    "version": "1.1.0"
                }
            }
        })

    elif method in ("notifications/initialized", "initialized"):
        return Response(status_code=200)

    elif method == "ping":
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": {}})

    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "select_content_matrix",
                        "description": "Tính toán và xếp hạng các tổ hợp 5 điểm chiến lược từ đồ thị tri thức 991 nodes. QUY TẮC BẮT BUỘC: 1) AI luôn luôn phải hỏi người dùng chọn 1 trong 3 chế độ sáng tạo ('default', 'research', 'deep') trước khi thực hiện. 2) Có thể đọc tài nguyên 'matrix://skill-guide' để nắm trọn cẩm nang vận hành và quy tắc copywriting độc bản.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "topic": {
                                    "type": "string",
                                    "description": "Chủ đề bài viết hoặc sản phẩm cần lên nội dung (Bắt buộc)"
                                },
                                "brand": {
                                    "type": "string",
                                    "description": "Tên thương hiệu hoặc dịch vụ"
                                },
                                "industry": {
                                    "type": "string",
                                    "description": "Ngành hàng (vd: giáo dục, tài chính, saas, f&b)"
                                },
                                "audience": {
                                    "type": "string",
                                    "description": "Chân dung khách hàng mục tiêu"
                                },
                                "insight": {
                                    "type": "string",
                                    "description": "Insight hoặc nỗi đau ngầm hiểu của khách hàng"
                                },
                                "marketing_goal": {
                                    "type": "string",
                                    "description": "Mục tiêu marketing (vd: nhận biết, chuyển đổi, tương tác)"
                                },
                                "count": {
                                    "type": "integer",
                                    "description": "Số lượng tổ hợp 5 điểm cần trả về (mặc định 3, tối đa 20)",
                                    "default": 3
                                },
                                "mode": {
                                    "type": "string",
                                    "description": "Chế độ sáng tạo: 'default' (mặc định), 'research' (nghiên cứu công thức, cấm demo), 'deep' (chuyên sâu N*100)",
                                    "enum": ["default", "research", "deep"],
                                    "default": "default"
                                },
                                "target_count": {
                                    "type": "integer",
                                    "description": "Số lượng ý tưởng mong muốn nhận (dành cho chế độ 'deep', ví dụ: 3, 5, 10)",
                                    "default": 3
                                },
                                "multiplier": {
                                    "type": "integer",
                                    "description": "Hệ số nhân ứng viên ở chế độ 'deep' (mặc định 100)",
                                    "default": 100
                                }
                            },
                            "required": ["topic"]
                        }
                    },
                    {
                        "name": "get_catalog_nodes",
                        "description": "Tra cứu nhanh kho công thức copywriting (ContentFormula), góc tiếp cận (ContentAngle), mẫu tiêu đề (HeadlineTemplate), dạng bài (ContentType).",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "description": "Loại catalog cần tra: ContentFormula, ContentAngle, SuccessPattern, HeadlineTemplate, ContentType",
                                    "default": "ContentFormula"
                                },
                                "search": {
                                    "type": "string",
                                    "description": "Từ khoá cần tìm"
                                }
                            }
                        }
                    },
                    {
                        "name": "validate_combination",
                        "description": "Thẩm định độ tương thích và phát hiện xung đột giữa các thành phần trong tổ hợp 5 điểm (Angle, Formula, Pattern, Headline, Type) theo đồ thị tri thức 991 nodes.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "angle": {"type": "string", "description": "Mã hoặc tên Content Angle (ví dụ: CA01)"},
                                "formula": {"type": "string", "description": "Mã hoặc tên Content Formula (ví dụ: CF01)"},
                                "pattern": {"type": "string", "description": "Mã hoặc tên Success Pattern (ví dụ: SP01)"},
                                "headline": {"type": "string", "description": "Mã hoặc tên Headline Template (ví dụ: HT01)"},
                                "type": {"type": "string", "description": "Mã hoặc tên Content Type (ví dụ: CT01)"}
                            }
                        }
                    }
                ]
            }
        })

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {}) or {}

        if tool_name == "select_content_matrix":
            count = min(20, max(1, int(args.get("count", 3))))
            mode = str(args.get("mode", "default")).lower().strip()
            target_count = min(10, max(1, int(args.get("target_count", 3))))
            multiplier = min(200, max(10, int(args.get("multiplier", 100))))
            brief_dict = {
                "topic": args.get("topic", ""),
                "brand": args.get("brand", ""),
                "industry": args.get("industry", ""),
                "audience": args.get("audience", ""),
                "insight": args.get("insight", ""),
                "marketing_goal": args.get("marketing_goal", ""),
            }
            try:
                raw_res = select_combinations.run(
                    matrix_data,
                    brief_dict,
                    count=count,
                    diversity=0.35,
                    pool_size=max(30, count * 3),
                    mode=mode,
                    target_count=target_count,
                    multiplier=multiplier,
                )

                formatted = []
                for item in raw_res.get("combinations", []):
                    fp = item.get("five_points", {})
                    angle = fp.get("content_angle", {})
                    formula = fp.get("content_formula", {})
                    pattern = fp.get("success_pattern", {})
                    headline = fp.get("headline_template", {})
                    ctype = fp.get("content_type", {})
                    sample_hl = (headline.get("examples") and headline["examples"][0]) or headline.get("template", "")

                    card_text = (
                        f"### Tổ Hợp #{item['rank']} (Điểm: {item.get('score', 0):.1f} - {item.get('selection_mechanism', 'brief')})\n"
                        f"- **🎯 Content Angle (Góc tiếp cận)**: {angle.get('name')} ({angle.get('code')})\n"
                        f"  *Định hướng*: {angle.get('direction') or angle.get('description')}\n"
                        f"- **📐 Content Formula (Công thức)**: {formula.get('name')} ({formula.get('code')})\n"
                        f"  *Cấu trúc*: {' -> '.join(formula.get('structure', []))}\n"
                        f"- **⚡ Success Pattern (Tâm lý)**: {pattern.get('name')} ({pattern.get('code')})\n"
                        f"  *Cơ chế*: {pattern.get('mechanism') or pattern.get('description')}\n"
                        f"- **🏷️ Headline Template (Tiêu đề gợi ý)**: \"{sample_hl}\"\n"
                        f"  *Khuôn mẫu*: {headline.get('template')}\n"
                        f"- **📱 Content Type (Định dạng đề xuất)**: {ctype.get('name')} ({ctype.get('code')})\n"
                    )

                    # Bổ sung khung research nếu ở chế độ research
                    if mode == "research" and item.get("research_framework"):
                        rf = item["research_framework"]
                        c_res = rf.get("cau_hoi_research", {})
                        f_what = c_res.get("cong_thuc_la_gi", {})
                        f_how = c_res.get("cach_ap_dung_hieu_qua", {})
                        card_text += (
                            f"\n🔬 **BÁO CÁO RESEARCH BẮT BUỘC (Chế độ Research):**\n"
                            f"  1. **Công thức đó là gì?**: {f_what.get('ban_chat_giai_phau', '')}\n"
                            f"  2. **Cách áp dụng hiệu quả?**: {f_how.get('huong_dan_thuc_thi', '')}\n"
                            f"  *Cạm bẫy cần tránh*: {f_how.get('cam_bay_can_tranh', '')}\n"
                            f"  ⚠️ *Yêu cầu sáng tạo*: {rf.get('yeu_cau_sang_tao_bat_buoc', '')}\n"
                        )

                    # Bổ sung scorecard nếu ở chế độ deep
                    if mode == "deep" and item.get("deep_scorecard"):
                        ds = item["deep_scorecard"]
                        card_text += (
                            f"\n⚡ **ĐÁNH GIÁ CHUYÊN SÂU (Deep Mode):**\n"
                            f"  - Độ tương thích với brief: {ds.get('prompt_relevance_pct', 0)}%\n"
                            f"  - Điểm hiệu quả chuyển đổi: {ds.get('overall_effectiveness_score', 0)}/100\n"
                            f"  - Lý do tuyển chọn: {ds.get('selection_rationale', '')}\n"
                        )

                    formatted.append(card_text)

                header_prefix = "## KẾT QUẢ CONTENT MATRIX 10B IDEAS"
                if mode == "research":
                    header_prefix += " — CHẾ ĐỘ RESEARCH"
                elif mode == "deep":
                    de = raw_res.get("deep_evaluation", {})
                    header_prefix += f" — CHẾ ĐỘ CHUYÊN SÂU (Đã trích xuất & thẩm định {de.get('total_candidates_extracted', 0)} ứng viên từ đồ thị 991 nodes)"

                text_response = (
                    f"{header_prefix}\n"
                    f"Đã phân tích brief và tuyển chọn ra {len(raw_res.get('combinations', []))} tổ hợp tối ưu nhất:\n\n"
                    + "\n\n".join(formatted)
                )

                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": text_response
                            }
                        ],
                        "structured_data": raw_res
                    }
                })
            except Exception as exc:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Lỗi khi tính toán tổ hợp Content Matrix: {str(exc)}"
                            }
                        ],
                        "isError": True
                    }
                })

        elif tool_name == "get_catalog_nodes":
            cat_type = args.get("type", "ContentFormula")
            search = args.get("search", "")
            items = []
            nodes = matrix_data.by_type.get(cat_type, [])
            for node in nodes:
                nid = node.get("code") or node.get("id") or ""
                label = node.get("name") or node.get("description") or nid
                if search and search.lower() not in (nid.lower() + " " + label.lower()):
                    continue
                items.append(f"- **{nid}**: {label} — *{node.get('description', '')}*")

            content_text = f"### Danh mục {cat_type} ({len(items)} mục):\n" + "\n".join(items[:25])
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": content_text
                        }
                    ]
                }
            })

        elif tool_name == "validate_combination":
            combo = args.get("combination", args)
            codes = [combo.get(k) for k in ("angle", "formula", "pattern", "headline", "type") if combo.get(k)]
            valid_codes = [c for c in codes if c in matrix_data.nodes]
            conflicts = []
            for i in range(len(valid_codes)):
                for j in range(i + 1, len(valid_codes)):
                    c1, c2 = valid_codes[i], valid_codes[j]
                    weight = matrix_data.weight(c1, c2)
                    if weight < 0.40:
                        conflicts.append({"pair": [c1, c2], "weight": weight, "note": "Độ tương thích thấp (< 0.40)"})

            if conflicts:
                msg = f"⚠️ Phát hiện {len(conflicts)} cặp có độ tương thích thấp trong tổ hợp:\n"
                for cf in conflicts:
                    msg += f"- `{cf['pair'][0]}` và `{cf['pair'][1]}`: Trọng số tương thích {cf['weight']:.2f} (Khuyến nghị xem xét thay thế)\n"
            else:
                msg = f"✅ Tổ hợp 5 điểm ({', '.join(valid_codes) if valid_codes else 'đã kiểm tra'}) hoàn toàn tương thích và hài hòa trên đồ thị tri thức 991 nodes!"

            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": msg}],
                    "structured_data": {"valid_codes": valid_codes, "conflicts": conflicts, "is_valid": len(conflicts) == 0}
                }
            })

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Không tìm thấy tool: {tool_name}"}
        })

    elif method == "prompts/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "prompts": [
                    {
                        "name": "content_matrix_director",
                        "description": "Kích hoạt vai trò Elite Creative Director & Master Copywriter với 3 Chế độ Sáng tạo (Mặc định, Research, Chuyên sâu). Hướng dẫn quy trình từ tiếp nhận brief, trích xuất tổ hợp 5 điểm đến hoàn thiện bài viết.",
                        "arguments": [
                            {
                                "name": "topic",
                                "description": "Chủ đề bài viết hoặc sản phẩm cần lên chiến dịch (Bắt buộc)",
                                "required": True
                            },
                            {
                                "name": "mode",
                                "description": "Chế độ sáng tạo: 'default' (Mặc định), 'research' (Nghiên cứu công thức, cấm demo), hoặc 'deep' (Chuyên sâu N*100)",
                                "required": False
                            },
                            {
                                "name": "brand",
                                "description": "Tên thương hiệu hoặc dịch vụ",
                                "required": False
                            },
                            {
                                "name": "audience",
                                "description": "Khách hàng mục tiêu",
                                "required": False
                            },
                            {
                                "name": "target_count",
                                "description": "Số ý tưởng mong muốn nhận nếu ở chế độ 'deep' (ví dụ: 3, 5, 10)",
                                "required": False
                            }
                        ]
                    },
                    {
                        "name": "creative_mode_gateway",
                        "description": "Câu hỏi mở đầu tương tác chuẩn mực để hỏi người dùng lựa chọn 1 trong 3 chế độ sáng tạo trước khi phân tích brief.",
                        "arguments": [
                            {
                                "name": "topic",
                                "description": "Chủ đề brief người dùng vừa nhập",
                                "required": False
                            }
                        ]
                    }
                ]
            }
        })

    elif method == "prompts/get":
        prompt_name = params.get("name")
        p_args = params.get("arguments", {}) or {}

        if prompt_name == "content_matrix_director":
            topic = p_args.get("topic", "")
            mode = str(p_args.get("mode", "default")).lower().strip()
            brand = p_args.get("brand", "")
            audience = p_args.get("audience", "")
            try:
                target_count = int(p_args.get("target_count", 3))
            except (ValueError, TypeError):
                target_count = 3

            if mode == "research":
                mode_instruction = (
                    "### QUY TRÌNH CHẾ ĐỘ RESEARCH (NGHIÊN CỨU SÂU & ĐỘC BẢN)\n"
                    "1. Gọi công cụ `select_content_matrix` với mode='research'.\n"
                    "2. Với mỗi tổ hợp 5 điểm nhận được, BẮT BUỘC trả lời 2 câu hỏi research cấu trúc:\n"
                    "   - CÂU HỎI 1: Công thức đó là gì? (Giải phẫu cấu trúc node & cơ chế tâm lý tác động).\n"
                    "   - CÂU HỎI 2: Cách áp dụng hiệu quả? (Đòn bẩy hành vi & cạm bẫy cần tránh cho brief này).\n"
                    "3. TUYỆT ĐỐI CẤM: Không sử dụng bất kỳ câu từ, ví dụ hay mô tả demo có sẵn nào từ hệ thống.\n"
                    "4. ÉP SÁNG TẠO ĐỘC BẢN: Viết bài hoàn chỉnh mới 100% dựa trên khung ý tưởng trích xuất."
                )
            elif mode == "deep":
                mode_instruction = (
                    f"### QUY TRÌNH CHẾ ĐỘ CHUYÊN SÂU (DEEP SAMPLING {target_count} x 100)\n"
                    f"1. Gọi công cụ `select_content_matrix` với mode='deep', target_count={target_count}, multiplier=100.\n"
                    f"2. Động cơ sẽ trích xuất {target_count * 100} ứng viên từ đồ thị 991 nodes, tự động đối chiếu ngữ cảnh và đánh giá khắt khe theo 3 tiêu chí: Relevance Fit, Psychology Conversion, Feasibility.\n"
                    f"3. Trình bày báo cáo phễu thẩm định (Evaluation Funnel) và xuất bản đúng {target_count} ý tưởng tinh hoa nhất kèm bảng điểm scorecard chi tiết."
                )
            else:
                mode_instruction = (
                    "### QUY TRÌNH CHẾ ĐỘ MẶC ĐỊNH (DEFAULT)\n"
                    "1. Gọi công cụ `select_content_matrix` với mode='default'.\n"
                    "2. Nhận các tổ hợp 5 điểm (Angle -> Formula -> Pattern -> Headline -> Type) và sản xuất nội dung hoàn chỉnh dùng được ngay."
                )

            instruction_text = (
                "Bạn là Elite Creative Director + Master Copywriter vận hành trên MatrixContent Knowledge Graph (991 nodes, 69,720 edges).\n\n"
                f"THÔNG TIN BRIEF HIỆN TẠI:\n"
                f"- Chủ đề: {topic or '(Chưa xác định - hãy hỏi người dùng)'}\n"
                f"- Thương hiệu: {brand or '(Chưa cung cấp)'}\n"
                f"- Khách hàng mục tiêu: {audience or '(Chưa cung cấp)'}\n\n"
                f"{mode_instruction}\n\n"
                "QUY TẮC VĂN PHONG BẮT BUỘC:\n"
                "- Tự nhiên, sống động, đanh thép như người thật viết.\n"
                "- CẤM TUYỆT ĐỐI văn AI sáo rỗng: cấm 'giải pháp toàn diện', 'tối ưu hóa', 'nâng tầm', 'đồng hành cùng', 'uy tín hàng đầu', 'không thể phủ nhận rằng'.\n"
                "- Mỗi nội dung phải có người, có cảnh, có chi tiết giác quan thật. Trừu tượng là lỗi."
            )

            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "description": f"Workflow Creative Director cho chủ đề: {topic} (Chế độ: {mode})",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": instruction_text
                            }
                        }
                    ]
                }
            })

        elif prompt_name == "creative_mode_gateway":
            topic = p_args.get("topic", "")
            gateway_text = (
                f"Chào bạn! Tôi đã nhận được chủ đề: '{topic or 'nội dung sáng tạo'}'.\n\n"
                "Trước khi khởi động động cơ đồ thị tri thức Content Matrix (991 nodes, 69,720 edges), xin mời bạn chọn 1 trong 3 Chế độ Sáng tạo:\n\n"
                "1️⃣ **Chế độ Mặc định (Default)**: Trích xuất các tổ hợp 5 điểm chiến lược tối ưu và sản xuất nội dung hoàn chỉnh dùng được ngay.\n"
                "2️⃣ **Chế độ Research (Nghiên cứu)**: Nghiên cứu giải phẫu chiều sâu công thức ('Công thức đó là gì?' & 'Cách áp dụng hiệu quả?'). Cấm dùng văn bản mẫu, ép AI sáng tạo độc bản 100%.\n"
                "3️⃣ **Chế độ Chuyên sâu (Deep)**: Nhập số lượng ý tưởng bạn mong muốn ($N$). Hệ thống sẽ nhân với 100 ($N \\times 100$) để trích xuất hàng trăm đến hàng nghìn ứng viên, chạy phễu sàng lọc dữ liệu đa chiều và tuyển chọn đúng $N$ ý tưởng xuất sắc nhất.\n\n"
                "👉 Bạn muốn triển khai theo **Chế độ 1, 2 hay 3**?"
            )
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "description": "Câu hỏi mở đầu tương tác Gateway 3 chế độ sáng tạo",
                    "messages": [
                        {
                            "role": "assistant",
                            "content": {
                                "type": "text",
                                "text": gateway_text
                            }
                        }
                    ]
                }
            })

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Không tìm thấy prompt: {prompt_name}"}
        })

    elif method == "resources/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resources": [
                    {
                        "uri": "matrix://skill-guide",
                        "name": "Content Matrix Skill & Operational Guide",
                        "description": "Toàn văn tài liệu hướng dẫn vận hành, quy tắc 5 điểm và 3 chế độ sáng tạo từ SKILL.md.",
                        "mimeType": "text/markdown"
                    },
                    {
                        "uri": "matrix://catalogs/formulas",
                        "name": "Copywriting Formulas Catalog",
                        "description": "Danh mục 150+ công thức copywriting đã cấu trúc hóa trong đồ thị tri thức.",
                        "mimeType": "application/json"
                    },
                    {
                        "uri": "matrix://catalogs/angles",
                        "name": "Content Angles Catalog",
                        "description": "Danh mục 90+ góc tiếp cận nội dung và đòn bẩy tâm lý khán giả.",
                        "mimeType": "application/json"
                    },
                    {
                        "uri": "matrix://graph-summary",
                        "name": "MatrixContent Graph Metrics Summary",
                        "description": "Thông số tổng quan về đồ thị tri thức (991 nodes, 69,720 edges).",
                        "mimeType": "application/json"
                    }
                ]
            }
        })

    elif method == "resources/read":
        uri = params.get("uri", "")
        if uri == "matrix://skill-guide":
            skill_path = os.path.join(SKILL_DIR, "SKILL.md")
            content = ""
            if os.path.exists(skill_path):
                with open(skill_path, "r", encoding="utf-8") as f:
                    content = f.read()
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    ]
                }
            })
        elif uri == "matrix://catalogs/formulas":
            nodes = matrix_data.by_type.get("ContentFormula", []) if matrix_data else []
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(nodes, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            })
        elif uri == "matrix://catalogs/angles":
            nodes = matrix_data.by_type.get("ContentAngle", []) if matrix_data else []
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(nodes, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            })
        elif uri == "matrix://graph-summary":
            summary = {
                "nodes_count": len(matrix_data.nodes) if matrix_data else 0,
                "edges_count": (matrix_data.graph_meta.get("total_edges") or 69720) if matrix_data else 0,
                "node_types": {k: len(v) for k, v in matrix_data.by_type.items()} if matrix_data else {},
                "relations": list(matrix_data.relations.keys()) if matrix_data else []
            }
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(summary, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            })
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": f"Resource không tồn tại: {uri}"}
        })

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Phương thức không hỗ trợ: {method}"}
    })


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
        mode = (payload.mode or "default").lower().strip()
        result = select_combinations.run(
            matrix_data,
            raw_brief,
            count=payload.count if mode != "deep" else (payload.target_count or 3),
            diversity=payload.diversity,
            seed=payload.seed,
            explain=payload.explain,
            pool_size=max(30, payload.count * 3),
            mode=mode,
            target_count=payload.target_count or 3,
            multiplier=payload.multiplier or 100,
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

        /* 3 Creative Modes Switcher */
        .mode-selector {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.5rem;
            margin-bottom: 1.25rem;
        }
        .mode-btn {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 0.65rem 0.5rem;
            color: var(--text-muted);
            cursor: pointer;
            text-align: center;
            transition: all 0.2s;
        }
        .mode-btn:hover {
            border-color: rgba(255, 107, 0, 0.4);
            background: rgba(255, 107, 0, 0.06);
            color: white;
        }
        .mode-btn.active {
            background: rgba(255, 107, 0, 0.15);
            border-color: var(--primary);
            color: white;
            box-shadow: 0 0 15px rgba(255, 107, 0, 0.25);
        }
        .mode-btn-title {
            font-size: 0.85rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.35rem;
        }
        .mode-btn-desc {
            font-size: 0.68rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
            line-height: 1.2;
        }
        .mode-banner {
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 0.82rem;
            margin-bottom: 1.25rem;
            line-height: 1.45;
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
        }
        .mode-banner-default {
            background: rgba(56, 189, 248, 0.08);
            border: 1px solid rgba(56, 189, 248, 0.2);
            color: #38BDF8;
        }
        .mode-banner-research {
            background: rgba(168, 85, 247, 0.1);
            border: 1px solid rgba(168, 85, 247, 0.3);
            color: #C084FC;
        }
        .mode-banner-deep {
            background: rgba(255, 107, 0, 0.1);
            border: 1px solid rgba(255, 107, 0, 0.3);
            color: var(--primary-glow);
        }

        .research-card {
            margin-top: 0.85rem;
            padding: 0.85rem;
            background: rgba(168, 85, 247, 0.08);
            border: 1px solid rgba(168, 85, 247, 0.25);
            border-radius: 8px;
            font-size: 0.84rem;
            color: #E2E8F0;
        }
        .research-title {
            font-weight: 700;
            color: #C084FC;
            margin-bottom: 0.4rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .deep-funnel-card {
            background: rgba(255, 107, 0, 0.08);
            border: 1px solid rgba(255, 107, 0, 0.25);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1.25rem;
            font-size: 0.85rem;
        }
        .deep-metric-row {
            display: flex;
            gap: 1.5rem;
            margin-top: 0.5rem;
            flex-wrap: wrap;
        }
        .deep-metric-item {
            background: rgba(0, 0, 0, 0.3);
            padding: 0.4rem 0.75rem;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.08);
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
                <span class="badge badge-primary">3 Chế Độ Sáng Tạo</span>
                <span class="badge">GPT Action & MCP Ready</span>
            </div>
        </header>

        <section class="hero">
            <h2>Ý Tưởng Triệu View Nối Liền 5 Điểm Chiến Lược</h2>
            <p>Vận hành trên đồ thị tri thức MatrixContent. Hỗ trợ 3 chế độ sáng tạo: Mặc định, Research (ép phân tích công thức, cấm demo) và Chuyên sâu (trích xuất N × 100 & AI thẩm định đa tầng).</p>
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
                    <div class="card-title">📝 Thiết Lập Brief & Chế Độ</div>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">JSON Engine v2.0</span>
                </div>

                <!-- 3 Creative Modes Selector -->
                <div class="mode-selector">
                    <button type="button" class="mode-btn active" id="btnModeDefault" onclick="setMode('default')">
                        <div class="mode-btn-title">⚡ Mặc định</div>
                        <div class="mode-btn-desc">Chuẩn 5 điểm</div>
                    </button>
                    <button type="button" class="mode-btn" id="btnModeResearch" onclick="setMode('research')">
                        <div class="mode-btn-title">🔬 Research</div>
                        <div class="mode-btn-desc">Phân tích & cấm demo</div>
                    </button>
                    <button type="button" class="mode-btn" id="btnModeDeep" onclick="setMode('deep')">
                        <div class="mode-btn-title">🎯 Chuyên sâu</div>
                        <div class="mode-btn-desc">Trích xuất N×100</div>
                    </button>
                </div>

                <div id="modeBanner" class="mode-banner mode-banner-default">
                    <span>💡 <strong>Chế độ Mặc định:</strong> Trích xuất nhanh các tổ hợp 5 điểm tối ưu nhất từ đồ thị 991 nodes cho brief tiếp thị.</span>
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
                            <label id="countLabel" class="form-label">Số hướng trả về (1-10)</label>
                            <input type="number" id="count" class="form-control" value="3" min="1" max="10" oninput="updateDeepMultiplier()">
                            <div id="deepMultiplierHint" style="display:none; font-size:0.75rem; color:var(--primary-glow); margin-top:0.35rem;">
                                🚀 Hệ thống sẽ trích xuất: <strong id="deepExtractCount">300</strong> ý tưởng (N × 100) để AI thẩm định.
                            </div>
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
                        <p>Nhập brief bên trái, chọn <strong>Chế độ Sáng tạo</strong> mong muốn rồi bấm <strong>"Tính toán 5 Điểm"</strong> để xem kết quả.</p>
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

        let currentMode = 'default';

        function setMode(mode) {
            currentMode = mode;
            document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
            const banner = document.getElementById('modeBanner');
            const countLabel = document.getElementById('countLabel');
            const deepHint = document.getElementById('deepMultiplierHint');

            banner.className = 'mode-banner';
            if (mode === 'default') {
                document.getElementById('btnModeDefault').classList.add('active');
                banner.classList.add('mode-banner-default');
                banner.innerHTML = `<span>💡 <strong>Chế độ Mặc định:</strong> Trích xuất nhanh các tổ hợp 5 điểm tối ưu nhất từ đồ thị 991 nodes cho brief tiếp thị.</span>`;
                countLabel.innerText = "Số hướng trả về (1-10)";
                deepHint.style.display = 'none';
            } else if (mode === 'research') {
                document.getElementById('btnModeResearch').classList.add('active');
                banner.classList.add('mode-banner-research');
                banner.innerHTML = `<span>🔬 <strong>Chế độ Research:</strong> Ép AI đặt câu hỏi phân tích bản chất công thức & cách áp dụng hiệu quả. CẤM dùng ví dụ mẫu demo, ép AI sáng tạo nguyên bản 100%.</span>`;
                countLabel.innerText = "Số hướng trả về (1-10)";
                deepHint.style.display = 'none';
            } else if (mode === 'deep') {
                document.getElementById('btnModeDeep').classList.add('active');
                banner.classList.add('mode-banner-deep');
                banner.innerHTML = `<span>🎯 <strong>Chế độ Chuyên sâu:</strong> Bạn chọn số ý tưởng mong muốn nhận (N). Hệ thống trích xuất N × 100 ứng viên từ đồ thị 991 nodes, search dữ liệu & AI audit để chọn ra N ý tưởng xuất sắc nhất.</span>`;
                countLabel.innerText = "Số ý tưởng mong muốn nhận (N: 1–10)";
                deepHint.style.display = 'block';
                updateDeepMultiplier();
            }
        }

        function updateDeepMultiplier() {
            const countVal = parseInt(document.getElementById('count').value) || 3;
            document.getElementById('deepExtractCount').innerText = countVal * 100;
        }

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
            updateDeepMultiplier();
            runEngine();
        }

        async function runEngine() {
            const btn = document.getElementById('submitBtn');
            const results = document.getElementById('resultsContainer');
            const timing = document.getElementById('timingBadge');

            const countVal = parseInt(document.getElementById('count').value) || 3;
            const payload = {
                topic: document.getElementById('topic').value,
                brand: document.getElementById('brand').value,
                industry: document.getElementById('industry').value,
                audience: document.getElementById('audience').value,
                insight: document.getElementById('insight').value,
                marketing_goal: document.getElementById('marketing_goal').value,
                count: countVal,
                mode: currentMode,
                target_count: countVal,
                multiplier: 100
            };

            btn.disabled = true;
            btn.innerText = "⏳ Đang tính toán trên đồ thị...";
            timing.innerText = "";
            const scanCountText = currentMode === 'deep' ? `${countVal * 100} ứng viên` : '991 nodes';
            results.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 3rem;">Đang quét ${scanCountText} và tính toán đồ thị MatrixContent...</div>`;

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

                let htmlContent = '';

                // Header banner cho Chế độ Chuyên sâu
                if (currentMode === 'deep' && data.deep_evaluation) {
                    const de = data.deep_evaluation;
                    htmlContent += `
                    <div class="deep-funnel-card">
                        <div style="font-weight: 700; color: var(--primary-glow); margin-bottom: 0.25rem;">⚡ Báo Cáo Thẩm Định Chuyên Sâu (Deep Mode)</div>
                        <div style="color: var(--text-muted); font-size: 0.8rem;">Đã trích xuất và thẩm định đa chiều qua đồ thị 991 nodes để chọn ra ${data.combinations.length} ý tưởng xuất sắc nhất.</div>
                        <div class="deep-metric-row">
                            <div class="deep-metric-item">Ứng viên trích xuất: <strong style="color:var(--primary);">${de.total_candidates_extracted || (countVal * 100)}</strong></div>
                            <div class="deep-metric-item">Sàng lọc khả thi: <strong style="color:var(--accent-green);">${de.evaluation_funnel?.screened_viable || de.total_candidates_extracted}</strong></div>
                            <div class="deep-metric-item">Ý tưởng chắt lọc: <strong style="color:white;">${data.combinations.length}</strong></div>
                        </div>
                    </div>
                    `;
                }

                htmlContent += data.combinations.map(item => {
                    const fp = item.five_points || {};
                    const angle = fp.content_angle || {};
                    const formula = fp.content_formula || {};
                    const pattern = fp.success_pattern || {};
                    const headline = fp.headline_template || {};
                    const ctype = fp.content_type || {};
                    const sample = (headline.examples && headline.examples[0]) || headline.template || (angle.name + ' — Đột phá mới');

                    let researchBox = '';
                    if (currentMode === 'research' && item.research_framework) {
                        const rf = item.research_framework;
                        const q = rf.cau_hoi_research || {};
                        const qWhat = q.cong_thuc_la_gi || {};
                        const qHow = q.cach_ap_dung_hieu_qua || {};

                        researchBox = `
                        <div class="research-card">
                            <div class="research-title">🔬 Phân Tích Research Công Thức:</div>
                            <div style="margin-bottom: 0.5rem;">
                                <strong>1. Bản chất công thức:</strong> ${qWhat.ban_chat_giai_phau || ''}
                            </div>
                            <div style="margin-bottom: 0.5rem;">
                                <strong>2. Cách áp dụng hiệu quả:</strong> ${qHow.huong_dan_thuc_thi || ''}
                            </div>
                            <div style="font-size: 0.76rem; color: #FCA5A5; margin-top: 0.35rem;">
                                ⚠️ <strong>Cấm ví dụ demo:</strong> ${rf.yeu_cau_sang_tao_bat_buoc || ''}
                            </div>
                        </div>
                        `;
                    }

                    let deepScoreBox = '';
                    if (currentMode === 'deep' && item.deep_scorecard) {
                        const ds = item.deep_scorecard;
                        deepScoreBox = `
                        <div style="margin-top: 0.6rem; padding: 0.5rem 0.75rem; background: rgba(255, 107, 0, 0.1); border-radius: 6px; font-size: 0.8rem; color: var(--primary-glow);">
                            🎯 <strong>Độ tương thích với brief:</strong> ${ds.prompt_relevance_pct}% | <strong>Điểm chuyển đổi:</strong> ${ds.overall_effectiveness_score}/100
                            <div style="color: var(--text-muted); font-size: 0.75rem; margin-top: 0.2rem;">${ds.selection_rationale}</div>
                        </div>
                        `;
                    }

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
                        ${researchBox}
                        ${deepScoreBox}
                    </div>
                    `;
                }).join('');

                results.innerHTML = htmlContent;

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
