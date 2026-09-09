# Quy trình sáng tạo

## Mục lục
1. [Bước 1 — Chuẩn hóa brief (14 trường)](#1-bước-1--chuẩn-hóa-brief-14-trường)
2. [Schema brief JSON](#2-schema-brief-json)
3. [Bước 2 — Chọn hướng chiến lược](#3-bước-2--chọn-hướng-chiến-lược)
4. [Bước 3 — Sinh tổ hợp ứng viên](#4-bước-3--sinh-tổ-hợp-ứng-viên)
5. [Bước 4 — Chấm điểm](#5-bước-4--chấm-điểm)
6. [Bước 5 — Bảo đảm 10 hướng thực sự khác nhau](#6-bước-5--bảo-đảm-10-hướng-thực-sự-khác-nhau)
7. [Bước 6 — Phát triển thành nội dung](#7-bước-6--phát-triển-thành-nội-dung)
8. [Chạy script](#8-chạy-script)
9. [Khi nào được hỏi lại](#9-khi-nào-được-hỏi-lại)

---

## 1. Bước 1 — Chuẩn hóa brief (14 trường)

| # | Trường | Suy luận được không? | Mặc định khi thiếu |
|---|---|---|---|
| 1 | Chủ đề gốc | — | bắt buộc |
| 2 | Thương hiệu | Không | `null` → viết trung tính, dùng placeholder `[Thương hiệu]` |
| 3 | Ngành hàng | Thường có, từ chủ đề | suy luận, ghi rõ là giả định |
| 4 | Sản phẩm / dịch vụ | Thường có | suy luận từ ngành |
| 5 | Đối tượng mục tiêu | **Hỏi nếu không suy được** | — |
| 6 | Insight / vấn đề | Suy được từ đối tượng + ngành | tự đề xuất 1–2 insight, đánh dấu giả định |
| 7 | Mục tiêu marketing | **Hỏi nếu mơ hồ hoàn toàn** | suy từ động từ trong brief |
| 8 | Giai đoạn hành trình | Suy từ mục tiêu | map theo bảng §3 |
| 9 | Kênh truyền thông | Suy được | `["social"]` |
| 10 | Dạng nội dung mong muốn | Suy được | để engine chọn |
| 11 | Giọng điệu | Suy từ ngành + đối tượng | "gần gũi, rõ ràng, có chuyên môn" |
| 12 | Bằng chứng / tài nguyên sẵn có | Không | `[]` → **cấm mọi tổ hợp phụ thuộc số liệu** |
| 13 | CTA | Suy từ mục tiêu | map theo mục tiêu |
| 14 | Ràng buộc & nội dung cần tránh | Không | suy theo ngành (xem `output-contracts.md` §5) |

Trường 12 là trường bị bỏ quên nhiều nhất và gây hại nhất. **Không có bằng
chứng thì không được đề xuất hướng dựa trên số liệu, case study hay kết quả đo
lường** — hoặc phải ghi rõ đó là điều kiện cần xác minh.

## 2. Schema brief JSON

Ghi ra file rồi truyền vào `--brief`. Chỉ `topic` là bắt buộc.

```json
{
  "topic": "Cuộc thi học sinh giỏi quốc gia",
  "brand": "UCMAS",
  "industry": "Giáo dục trẻ em",
  "product": "Chương trình toán trí tuệ bàn tính",
  "audience": "Phụ huynh có con 7-14 tuổi tại thành phố",
  "insight": "Phụ huynh muốn con nổi bật nhưng sợ con áp lực",
  "marketing_goal": "Khuyến khích đăng ký tham gia",
  "goal_codes": ["RC12"],
  "journey_stage": "conversion",
  "awareness_stage": "product",
  "sophistication": 3,
  "channels": ["Facebook"],
  "content_type_hint": ["Caption social ngắn"],
  "tone": "ấm áp, tôn trọng phụ huynh, không hù dọa",
  "assets": ["ảnh lớp học", "lịch thi"],
  "cta": "Đăng ký vòng loại trước 30/9",
  "constraints": ["không cam kết giải thưởng", "không so sánh trẻ"],
  "avoid": ["gây áp lực thành tích", "chê bai trẻ"],
  "master_pillar_hint": [],
  "pillar_hint": [],
  "angle_hint": []
}
```

Ghi chú:
- `goal_codes` để trống → engine tự suy từ `marketing_goal` + `journey_stage`
  bằng khớp ngữ nghĩa với 24 Marketing Goal, và trả về `goal_inference` để bạn
  kiểm tra lại.
- `*_hint` là **ràng buộc cứng**: khai báo thì engine chỉ chọn trong đó.
  Dùng khi người dùng đã tự chọn Master Pillar hoặc Angle.
- `journey_stage`: `awareness` · `consideration` · `conversion` · `onboarding` ·
  `retention` · `advocacy`. Khai báo tường minh là **bộ lọc cứng** cho Marketing Goal.
- `awareness_stage` (Schwartz, quyết định **hình thức mở bài**):
  `unaware` · `problem` · `solution` · `product` · `most_aware`.
  Bỏ trống thì engine suy từ `journey_stage`. Chi tiết: `copy-craft.md` §2.
- `sophistication` 1–5 — mức bão hòa thị trường, quyết định **lời hứa còn hiệu lực
  hay không**. Không đi vào engine, nhưng bắt buộc dùng khi viết: `copy-craft.md` §3.
- `channels` được ánh xạ sang **hồ sơ kênh** có phương tiện bắt buộc và bị cấm.
  Định dạng thuộc phương tiện bị cấm sẽ bị **loại cứng**, không phải trừ điểm.
- `assets` xuất hiện lại trong kết quả dưới khóa `must_use_assets` —
  nội dung viết ra phải dùng, hoặc nói rõ vì sao không dùng.

## 3. Bước 2 — Chọn hướng chiến lược

Thứ tự quyết định: **Marketing Goal → Master Pillar → Pillar → Content Angle.**
Không đảo ngược. Chọn Angle trước rồi gán Goal là cách nhanh nhất tạo ra 10 ý
tưởng nghe hay nhưng không phục vụ mục tiêu nào.

Map giai đoạn → pillar ưu tiên (dùng khi brief không nêu goal code):

| Giai đoạn | Pillar chủ lực | Goal thường gặp |
|---|---|---|
| awareness | CJ01–CJ03, JT02–JT03, CO01, CO03 | RC01, RC02, RC04 |
| consideration | CJ05–CJ08, JT05–JT06, JT11, BR07 | RC03, RC05–RC08 |
| conversion | CJ09–CJ12, MM02, BR08, JT12, MM07 | RC09–RC12 |
| onboarding | CJ13, JT13, MM06 | RC13 |
| retention | CJ14–CJ16, JT14, CO11–CO13 | RC14–RC16 |
| advocacy | CJ17, CO07, CO14, BR15, CO15 | RC17, RC22, RC24 |

Năm điều **phải** xét ngoài từ khóa:
1. Mục tiêu kinh doanh thật (đăng ký? giữ chân? định vị?).
2. Trạng thái nhận thức của đối tượng — quyết định nên mở bằng vấn đề hay bằng giải pháp.
3. Insight — hướng nào chạm đúng mâu thuẫn nội tâm, không chỉ đúng nhân khẩu học.
4. Mức phù hợp thương hiệu — hướng gây tranh cãi có thể điểm cao nhưng brand không dám chạy.
5. Kênh + bằng chứng sẵn có — quyết định Content Type khả thi.

## 4. Bước 3 — Sinh tổ hợp ứng viên

### Ba cơ chế chọn Content Angle

Engine **không** bốc ngẫu nhiên, và cũng không chỉ chạy một lối. Ba cơ chế chạy
song song rồi hợp nhất vào một hồ ứng viên:

| Cơ chế | Nguyên tắc | Hạn ngạch trong 10 hướng cuối |
|---|---|---|
| `brief` | Khớp chủ đề, insight, mục tiêu và giai đoạn với Pillar rồi tới Angle | ≥ 4 |
| `industry` | Bỏ qua chủ đề, chỉ hỏi ngành này thường kể chuyện gì (hồ sơ 19 ngành trong overlay) | ≥ 2 |
| `random` | Bốc phân tầng theo Master Pillar trên toàn bộ 624 góc | ≥ 1 |

Hạn ngạch là **bắt buộc**: rubric vốn thiên về brief, nếu xếp hạng tự do thì hai
cơ chế kia không bao giờ lọt vào danh sách cuối và việc có ba cơ chế trở thành
vô nghĩa. Cơ chế `random` là nguồn duy nhất có thể chạm tới những góc mà hai cơ
chế kia không bao giờ xét tới.

### Phễu 30 → 10

1. Ba cơ chế góp góc → beam search dựng tổ hợp → chấm rubric.
2. Chọn **30 ý tưởng** vào shortlist theo tỉ lệ 50% brief / 30% industry / 20% random.
3. **Sàng tính khả thi** — chấm thứ rubric không đo:
   - sức sản xuất (`format_specs` từ Cao trở lên bị trừ)
   - đòi bằng chứng mà brief chưa khai `assets`
   - đòi tổ chức sự kiện trực tiếp (`CT40`, `CT46`, `CT47`, `CT55`)
   - xung đột mềm và số cạnh thiếu
   Kết quả: `khả thi` · `cân nhắc` · `loại`.
4. Loại các hướng bị đánh `loại`, rồi chốt **10 hướng** kèm hạn ngạch cơ chế.

Kết quả nằm ở `strategy.mechanism_mix`, `strategy.feasibility_screen` và
`feasibility` của từng hướng. Khi trình bày, **nêu rõ hướng nào đến từ cơ chế
nào** — hướng từ `random` thường là hướng bất ngờ nhất và đáng nói nhất.


Từ mỗi Content Angle ứng viên, mở rộng theo `COMPATIBLE_WITH` sang
ContentFormula, SuccessPattern, HeadlineTemplate, ContentType, rồi tính đủ
**10 cạnh** của tổ hợp (xem `knowledge-model.md` §8).

Ưu tiên trọng số cao. Cạnh vắng → phạt. Cặp nằm trong `AVOID_WITH` (khi dữ liệu
có) hoặc trong `avoid_rules` của semantic overlay → loại hoặc trừ nặng.

Ba quy tắc cứng:
- **Không bịa** mã, tên node, trọng số, quan hệ.
- Mọi suy luận không dựa trên cạnh thật phải mang cờ `semantic_fallback` và
  được nói rõ trong output là suy luận ngữ nghĩa.
- Content Type phải chở nổi Content Formula. Công thức 6–9 bước không nhét vừa
  caption ngắn hay story 15 giây — engine phạt qua `capacity_penalty`.

## 5. Bước 4 — Chấm điểm

Rubric 100 điểm, công thức tổng hợp và hình phạt: `scoring-and-diversity.md`.

## 6. Bước 5 — Bảo đảm 10 hướng thực sự khác nhau

Ngưỡng bắt buộc và cơ chế MMR: `scoring-and-diversity.md` §3–§4.
Tóm tắt: mỗi cặp hướng khác nhau ≥ 2/5 thành phần; toàn danh sách ≥ 4 Angle,
≥ 4 SuccessPattern, ≥ 3 ContentType khác nhau khi brief không giới hạn.

## 7. Bước 6 — Phát triển thành nội dung

1. **Đọc `structure` của Content Formula** rồi *quên tên nó đi*. Viết theo mạch
   tự nhiên. Người đọc không được nhận ra khung.
2. **Đọc `mechanism` của Success Pattern** — đây là thứ quyết định câu mở đầu và
   nhịp giữ chân, không phải trang trí.
3. **Viết lại Headline Template thành tiêu đề thật.** Template `[Kết quả] cho
   [đối tượng]: bắt đầu từ [bước nhỏ]` là khung. Đầu ra không được còn dấu ngoặc
   vuông. Không dịch cứng cấu trúc — giữ ý, đổi cú pháp cho tự nhiên.
4. **Tuân thủ `format_specs` và `suitable_channels` của Content Type.**
5. **Không bịa**: số liệu, giải thưởng, phản hồi khách hàng, tên người thật,
   cam kết kết quả, nghiên cứu khoa học. Thiếu → `[cần xác minh: ...]`.
6. **Cá nhân hóa** theo thương hiệu, đối tượng, kênh, giọng điệu trong brief.

## 8. Chạy script

```bash
python scripts/select_combinations.py --brief brief.json --count 10 --pretty
```

Cờ hữu ích:

| Cờ | Tác dụng |
|---|---|
| `--count N` | số hướng bàn giao, mặc định 10 |
| `--pool N` | số ý tưởng dựng ở vòng shortlist trước khi sàng, mặc định 30 |
| `--pretty` | JSON xuống dòng dễ đọc |
| `--explain` | kèm chi tiết từng cạnh và điểm thành phần |
| `--seed N` | đổi hạt ngẫu nhiên để lấy góc nhìn khác trên cùng brief |
| `--diversity F` | 0.0–1.0, mặc định 0.35; tăng để đa dạng hơn, giảm để bám sát brief |
| `--out FILE` | ghi ra file để đưa cho `validate_matrixcontent.py` |

Kiểm tra trước khi viết:

```bash
python scripts/validate_matrixcontent.py --result result.json --min-count 10
```

## 9. Khi nào được hỏi lại

**Hỏi** khi: không xác định được đối tượng và brief cho phép nhiều đối tượng
trái ngược · mục tiêu mơ hồ tới mức RC01 và RC12 đều hợp lý · brand ở ngành
pháp lý nhạy cảm mà không rõ ràng buộc.

**Không hỏi** khi: thiếu tone, thiếu CTA, thiếu kênh, thiếu ngành hàng suy được,
thiếu tên sản phẩm. Nêu giả định và đi tiếp.

Tối đa 3 câu hỏi, gộp trong một lượt. Không hỏi rồi lại hỏi tiếp.
