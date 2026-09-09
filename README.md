# Content Matrix 10B Ideas — OpenAI Agent Plugin & API

[![OpenAI Agent Plugin](https://img.shields.io/badge/OpenAI-Agent%20Plugin-00A67E?style=for-the-badge&logo=openai&logoColor=white)](https://developers.openai.com/plugins/build/plugins)
[![Vercel Deployed](https://img.shields.io/badge/Vercel-Deployed-black?style=for-the-badge&logo=vercel&logoColor=white)](https://content-matrix-10b-ideas.vercel.app)
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
3. **Standalone REST API** (FastAPI serverless trên Vercel)

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
     https://content-matrix-10b-ideas.vercel.app/openapi.json
     ```
   - ChatGPT sẽ tự động nạp các công cụ: `selectMatrixCombinations`, `getCatalogNodes`, `validateCombination`.
4. Nhấn **Save / Publish** để hoàn tất!

---

## 📡 API Endpoints (Vercel)

Base URL: `https://content-matrix-10b-ideas.vercel.app`

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
curl -X POST "https://content-matrix-10b-ideas.vercel.app/api/select" \
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
