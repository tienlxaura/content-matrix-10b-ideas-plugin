# Content Matrix 10B Ideas — OpenAI Agent Plugin & API

[![OpenAI Agent Plugin](https://img.shields.io/badge/OpenAI-Agent%20Plugin-00A67E?style=for-the-badge&logo=openai&logoColor=white)](https://developers.openai.com/plugins/build/plugins)
[![Vercel Deployed](https://img.shields.io/badge/Vercel-Deployed-black?style=for-the-badge&logo=vercel&logoColor=white)](https://content-matrix-10b-ideas-plugin.vercel.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **Universal Content Engine & Elite Creative Director** dành cho ChatGPT, Codex và các LLM hàng đầu. Vận hành dựa trên đồ thị tri thức **MatrixContent Knowledge Graph** (991 node, 69.720 cạnh) giúp biến brief sơ sài thành các sản phẩm câu chữ sắc bén, chuyển đổi cao và dùng được ngay.

---

## 🚀 Giới Thiệu

Mọi ý tưởng nội dung bách phát bách trúng đều cần sự liên kết chặt chẽ của **5 điểm chiến lược**:
```text
Content Angle → Content Formula → Success Pattern → Headline Template → Content Type
```
với **Marketing Goal** làm biển chỉ đường, **Customer Insight** làm nhiên liệu và **Offer** làm nền móng chuyển đổi.

Plugin này đóng gói toàn bộ kho tri thức, công thức và script tính toán scoring để chạy trực tiếp trên:
1. **ChatGPT Desktop & Codex** (chuẩn Agent Plugins với local marketplace)
2. **ChatGPT Web** (chuẩn Custom GPT Actions với OpenAPI 3.0)
3. **Standalone REST API & MCP Server** (FastAPI serverless trên Vercel)

---

## 🎨 3 Chế Độ Sáng Tạo Chuyên Biệt

Hệ thống hỗ trợ 3 chế độ sáng tạo tương tác tùy theo nhu cầu:

1. **⚡ Chế độ Mặc định (Default Mode):**
   - Sinh nhanh 5-10 tổ hợp 5 điểm tối ưu nhất dựa trên điểm số đồ thị.
   - Trả về pitch block và cấu trúc bài viết chuẩn hóa dùng được ngay.

2. **🔬 Chế độ Research (Research Mode):**
   - **Ép phân tích chuyên sâu:** AI bắt buộc phải trả lời 2 câu hỏi: *Công thức đó là gì?* (giải phẫu cấu trúc & tâm lý học) và *Cách áp dụng hiệu quả?* (chiến lược thực chiến, điểm chuyển đổi, cạm bẫy cần tránh).
   - **Cấm demo ví dụ:** Tuyệt đối không dùng ví dụ và mô tả mẫu có sẵn trong hệ thống. Ép AI phải tự sáng tạo nội dung mới 100% dựa trên khung ý tưởng trích xuất.

3. **🎯 Chế độ Chuyên sâu (Deep / Intensive Mode):**
   - **Hỏi số ý tưởng $N$:** Người dùng nhập số lượng ý tưởng mong muốn nhận (ví dụ $N = 3, 5, 10$).
   - **Trích xuất quy mô lớn $M = N \times 100$:** Hệ thống tự động trích xuất hàng trăm đến 1.000+ ứng viên từ đồ thị 991 nodes (thời gian < 1.5s).
   - **Search & AI Thẩm định đa tầng:** Hệ thống search dữ liệu liên quan, AI đánh giá mức độ phù hợp (% fit) và tiềm năng chuyển đổi so với prompt gốc, sau đó chắt lọc và trả ra đúng $N$ ý tưởng xuất sắc nhất kèm báo cáo phễu đánh giá.

---

## 🛠️ Cài Đặt & Sử Dụng

### Cách 1: ChatGPT Desktop & Codex (Agent Plugins)

1. Mở terminal và thêm repo này vào Codex Plugin Marketplace:
   ```bash
   codex plugin marketplace add tienlxaura/content-matrix-10b-ideas-plugin
   ```
2. Hoặc thêm entry sau vào file `.agents/plugins/marketplace.json` trong dự án của bạn:
   ```json
   {
     "name": "content-matrix-10b-ideas",
     "source": {
       "source": "local",
       "path": "./plugins/content-matrix-10b-ideas"
     },
     "policy": {
       "installation": "AVAILABLE",
       "authentication": "ON_INSTALL"
     },
     "category": "Marketing & Content"
   }
   ```
3. Mở ứng dụng **ChatGPT Desktop**, vào **Settings > Plugins**, bật Plugin **Content Matrix 10B Ideas**.

---

### Cách 2: ChatGPT Web (Custom GPT Actions)

1. Truy cập [ChatGPT GPT Builder](https://chatgpt.com/gpts/editor).
2. Tại tab **Configure**:
   - **Name**: Content Matrix 10B Ideas — Creative Director
   - **Description**: Elite Creative Director & Master Copywriter nối liền 5 điểm chiến lược.
   - **Instructions**: Dán nội dung từ file [`skills/content-matrix/SKILL.md`](skills/content-matrix/SKILL.md).
3. Kéo xuống mục **Actions > Create new action**:
   - Nhấn **Import from URL**.
   - Dán URL OpenAPI của hệ thống:
     ```text
     https://content-matrix-10b-ideas-plugin.vercel.app/openapi.json
     ```
   - ChatGPT sẽ tự động nạp các công cụ: `selectMatrixCombinations`, `getCatalogNodes`, `validateCombination`.
4. Nhấn **Save / Publish** để hoàn tất!

---

### Cách 3: Tích Hợp Full MCP Server (Model Context Protocol) — Khuyên Dùng ⭐

Tự động cập nhật 100% mỗi phiên làm việc, không cần copy-paste hay cấu hình lại khi hệ thống nâng cấp.

#### 1. Dành cho Cursor / Windsurf / Antigravity IDE / Cline:
Thêm cấu hình sau vào mục MCP Servers (`mcp_config.json`):
```json
{
  "mcpServers": {
    "content-matrix": {
      "type": "streamable-http",
      "url": "https://content-matrix-10b-ideas-plugin.vercel.app/mcp"
    }
  }
}
```

#### 2. Dành cho Claude Desktop:
Mở file `claude_desktop_config.json` và thêm:
```json
{
  "mcpServers": {
    "content-matrix": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://content-matrix-10b-ideas-plugin.vercel.app/mcp"
      ]
    }
  }
}
```

#### 3. Dành cho ChatGPT (Desktop / Web có hỗ trợ MCP):
Nhập trực tiếp endpoint MCP Streamable HTTP:
```text
https://content-matrix-10b-ideas-plugin.vercel.app/mcp
```

**Bộ tính năng Full MCP cung cấp:**
- 🛠️ **Tools**: `select_content_matrix` (Hỗ trợ 3 Chế độ: Mặc định, Research, Chuyên sâu), `get_catalog_nodes`, `validate_combination`.
- 📝 **Prompts**: `content_matrix_director` (Tự động nạp quy trình Creative Director vào ngữ cảnh), `creative_mode_gateway` (Câu hỏi mở đầu chọn chế độ).
- 📚 **Resources**: `matrix://skill-guide` (Tài liệu SKILL.md), `matrix://catalogs/formulas` (150+ công thức), `matrix://catalogs/angles` (90+ góc tiếp cận), `matrix://graph-summary` (Thông số đồ thị 991 nodes, 69.720 cạnh).

---

## 📡 API Endpoints (Vercel)

Base URL: `https://content-matrix-10b-ideas-plugin.vercel.app`

| Phương thức | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/` | Web Dashboard & Interactive Tester trực quan |
| `GET` | `/health` | Kiểm tra trạng thái hoạt động & số lượng node/cạnh |
| `GET` | `/plugin.json` | Manifest tiêu chuẩn OpenAI Agent Plugins |
| `GET` | `/.well-known/ai-plugin.json` | Manifest chuẩn OpenAI ChatGPT Plugin truyền thống |
| `GET` | `/openapi.json` | Đặc tả OpenAPI 3.0 phục vụ Custom GPT |
| `POST` | `/api/select` | Tính toán & xếp hạng các tổ hợp 5 điểm theo brief |
| `GET` | `/api/catalogs` | Tra cứu danh mục Angles, Formulas, Headlines, Types |
| `POST` | `/api/validate` | Thẩm định xung đột giữa các thành phần |

### Ví dụ gọi API:

```bash
curl -X POST "https://content-matrix-10b-ideas-plugin.vercel.app/api/select" \
     -H "Content-Type: application/json" \
     -d '{
       "topic": "Quảng cáo khoá học toán tư duy UCMAS",
       "brand": "UCMAS Việt Nam",
       "audience": "Phụ huynh có con 4-10 tuổi",
       "insight": "Phụ huynh sợ con nghiện màn hình, mất tập trung",
       "marketing_goal": "Khách nhắn tin fanpage để nhận tư vấn học thử",
       "count": 3
     }'
```

---

## 📂 Cấu Trúc Thư Mục

```text
content-matrix-10b-ideas-plugin/
├── plugin.json                 # Manifest chuẩn Agent Plugins (schema 1.0.0)
├── .codex-plugin/
│   └── plugin.json             # Manifest tương thích ngược Codex/ChatGPT
├── .well-known/
│   └── ai-plugin.json          # Manifest tương thích ChatGPT Plugins
├── openapi.json                # Đặc tả OpenAPI 3.0
├── mcp.json                    # Cấu hình MCP Server
├── vercel.json                 # Cấu hình Vercel Serverless
├── requirements.txt            # Thư viện Python
├── api/
│   └── index.py                # FastAPI Serverless backend & Web dashboard
├── skills/
│   └── content-matrix/
│       ├── SKILL.md            # Tri thức và quy tắc copywriting cốt lõi
│       ├── data/               # Đồ thị 991 node và 69.720 cạnh offline
│       ├── scripts/            # Engine scoring và tính toán 5 điểm
│       └── references/         # 13 tài liệu Playbook & Craft chuyên sâu
└── assets/
    ├── icon.png                # Icon plugin 128x128
    └── logo.png                # Logo Aura Matrix 512x512
```

---

## 📄 Bản Quyền & Tác Giả

- **Phát triển bởi**: [Aura Marketers](https://auramarketers.com)
- **Tác giả**: Le Xuan Tien (`tienlx@auramarketers.com`)
- **Giấy phép**: MIT License
