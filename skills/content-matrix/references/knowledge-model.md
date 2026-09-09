# Mô hình tri thức MatrixContent

## Mục lục
1. [Tám loại node và ý nghĩa](#1-tám-loại-node-và-ý-nghĩa)
2. [Quy ước mã](#2-quy-ước-mã)
3. [Năm Master Pillar](#3-năm-master-pillar)
4. [72 Pillar theo Master Pillar](#4-72-pillar-theo-master-pillar)
5. [24 Marketing Goal](#5-24-marketing-goal)
6. [Ngữ nghĩa 9 quan hệ](#6-ngữ-nghĩa-9-quan-hệ)
7. [Cấu trúc cạnh và trọng số](#7-cấu-trúc-cạnh-và-trọng-số)
8. [Mười cặp trong một tổ hợp 5 điểm](#8-mười-cặp-trong-một-tổ-hợp-5-điểm)
9. [Từ vựng tag](#9-từ-vựng-tag)
10. [Cách chọn Master Pillar](#10-cách-chọn-master-pillar)

---

## 1. Tám loại node và ý nghĩa

| Loại | Số lượng | Vai trò trong quyết định | Trường riêng |
|---|---|---|---|
| MasterPillar | 5 | Chọn **hệ quy chiếu** — nhìn vấn đề bằng lăng kính nào | `approach`, `central_question`, `pillar_prefix` |
| Pillar | 72 | Chọn **địa hạt nội dung** trong hệ quy chiếu đó | `role`, `scope` |
| ContentAngle | 624 | Chọn **góc nhìn cụ thể** — hạt nhân của ý tưởng | `direction` |
| ContentFormula | 44 | **Bộ xương** bài viết, thứ tự lập luận | `structure` (mảng các bước) |
| SuccessPattern | 66 | **Cơ chế tâm lý** khiến người đọc dừng lại và tin | `mechanism` |
| HeadlineTemplate | 96 | **Khung tiêu đề** — chỉ là khung, phải viết lại | `template` |
| ContentType | 60 | **Vật chứa** — định dạng và kênh phát hành | `format_specs`, `suitable_channels` |
| MarketingGoal | 24 | **Biến định hướng** — ưu tiên và loại bỏ tổ hợp | — |

Mọi node đều có: `id`, `code`, `type`, `name`, `description`, `parent_id`,
`tags`, `complexity` (low/medium/high), `source`, `status`.

`complexity` là tín hiệu thật cho khả năng triển khai: `high` đòi hỏi nhiều
bằng chứng, nhân sự hoặc thời gian hơn — dùng nó khi chấm điểm feasibility.

## 2. Quy ước mã

```
MasterPillar     MP01 – MP05
Pillar           {CJ|BR|MM|JT|CO} + 2 chữ số     ví dụ CJ09, BR14, MM02
ContentAngle     {Pillar}-A{2 chữ số}            ví dụ CJ09-A03
ContentFormula   CF01 – CF44
SuccessPattern   MH01 – MH66
HeadlineTemplate HT001 – HT096   (ba chữ số)
ContentType      CT01 – CT60
MarketingGoal    RC01 – RC24
```

Mã `ContentAngle` **tự mang** thông tin pillar cha: `CJ09-A03` thuộc `CJ09`,
thuộc `MP01`. Không cần tra để biết cha.

Không bao giờ viết mã ngoài các dải trên. `HT12` sai, `HT012` đúng.

## 3. Năm Master Pillar

| Mã | Prefix | Tên | Approach | Câu hỏi trung tâm |
|---|---|---|---|---|
| MP01 | CJ | Hành trình khách hàng | Customer-centric | Khách hàng đang ở đâu trong hành trình nhận thức, cân nhắc, mua, sử dụng và lan tỏa? |
| MP02 | BR | Kiến tạo thương hiệu | Brand-centric | Thương hiệu muốn được hiểu, cảm nhận, ghi nhớ và lựa chọn như thế nào? |
| MP03 | MM | Marketing Mix 7P | Business-centric | Thương hiệu tạo, định giá, phân phối, truyền thông và vận hành giá trị như thế nào? |
| MP04 | JT | Nhu cầu – Giải pháp JTBD | Problem/Solution-centric | Trong một hoàn cảnh cụ thể, khách hàng "thuê" sản phẩm để tạo tiến bộ nào? |
| MP05 | CO | Quan hệ – Cộng đồng – Văn hóa | Relationship/Community-centric | Điều gì khiến các bên liên quan muốn kết nối, tham gia, tin tưởng, gắn bó và lan tỏa? |

Khác biệt thực dụng giữa MP01 và MP04: **MP01 đi theo trạng thái nhận thức**
(chưa biết → cân nhắc → mua → dùng → giới thiệu). **MP04 đi theo hoàn cảnh và
tiến bộ cần đạt** (hoàn cảnh nào, đang xoay xở bằng gì, vì sao chưa đủ). Cùng
một sản phẩm, MP01 cho ra nội dung dẫn dắt theo phễu, MP04 cho ra nội dung
"đúng hoàn cảnh của tôi".

## 4. 72 Pillar theo Master Pillar

**MP01 · CJ — Hành trình khách hàng (17)**
CJ01 Bối cảnh phát sinh nhu cầu · CJ02 Vấn đề và nỗi đau · CJ03 Mong muốn và mục tiêu ·
CJ04 Nhận thức nguyên nhân · CJ05 Kiến thức nền tảng · CJ06 Nhận biết giải pháp ·
CJ07 Tiêu chí lựa chọn · CJ08 So sánh và cân nhắc · CJ09 Xây dựng niềm tin ·
CJ10 Xử lý phản đối · CJ11 Trải nghiệm và kiểm chứng · CJ12 Chuyển đổi ·
CJ13 Onboarding · CJ14 Trải nghiệm sử dụng · CJ15 Tiến bộ và kết quả ·
CJ16 Duy trì và phát triển · CJ17 Lan tỏa và kích hoạt lại

**MP02 · BR — Kiến tạo thương hiệu (19)**
BR01 Nguồn gốc và mục đích tồn tại · BR02 Tầm nhìn và sứ mệnh · BR03 Khách hàng và insight ·
BR04 Định vị thương hiệu · BR05 Giá trị và triết lý · BR06 Lời hứa thương hiệu ·
BR07 Điểm khác biệt · BR08 Bằng chứng thuyết phục · BR09 Sản phẩm và tài sản trí tuệ ·
BR10 Hệ sinh thái thương hiệu · BR11 Nhận diện và cá tính · BR12 Con người và văn hóa ·
BR13 Trải nghiệm thương hiệu · BR14 Danh tiếng và thành tựu · BR15 Câu chuyện khách hàng ·
BR16 Chiến dịch và hợp tác · BR17 Dẫn dắt thị trường · BR18 Cộng đồng và trách nhiệm xã hội ·
BR19 Đổi mới và tương lai

**MP03 · MM — Marketing Mix 7P (7)**
MM01 Product · MM02 Price · MM03 Place · MM04 Promotion · MM05 People ·
MM06 Process · MM07 Physical Evidence

**MP04 · JT — Nhu cầu – Giải pháp JTBD (14)**
JT01 Công việc khách hàng cần hoàn thành · JT02 Bối cảnh và tác nhân kích hoạt ·
JT03 Nỗi đau hiện tại · JT04 Kết quả mong muốn · JT05 Giải pháp đang sử dụng ·
JT06 Hạn chế của giải pháp cũ · JT07 Rào cản chuyển đổi · JT08 Cơ chế giải quyết ·
JT09 Tính năng và lợi ích · JT10 Tình huống sử dụng · JT11 So sánh giải pháp ·
JT12 Bằng chứng kết quả · JT13 Hướng dẫn áp dụng · JT14 Kết quả và mở rộng

**MP05 · CO — Quan hệ – Cộng đồng – Văn hóa (15)**
CO01 Niềm tin và bản sắc chung · CO02 Kiến thức chung · CO03 Cảm hứng và chuyển đổi ·
CO04 Đối thoại và tương tác · CO05 Chuỗi nội dung và nghi thức · CO06 Câu chuyện thành viên ·
CO07 UGC và bằng chứng xã hội · CO08 Sự kiện và trải nghiệm chung · CO09 Chuyên gia và đại sứ ·
CO10 Đồng sáng tạo · CO11 Sản phẩm và đặc quyền · CO12 Chăm sóc và lắng nghe ·
CO13 Ghi nhận và trung thành · CO14 Giới thiệu và lan tỏa · CO15 Tác động xã hội

Mỗi Pillar chứa 6–12 Content Angle. Tra tên và `direction` đầy đủ trong
`data/catalogs/content-angles.json`.

## 5. 24 Marketing Goal

| Mã | Tên | Nguyên tắc cốt lõi |
|---|---|---|
| RC01 | Tạo nhận biết vấn đề | Làm người xem nhận ra vấn đề trước khi nói sâu về giải pháp |
| RC02 | Giáo dục nền tảng | Ưu tiên rõ và đúng trước khi thuyết phục |
| RC03 | Chẩn đoán nguyên nhân | Biến vấn đề chung thành chẩn đoán có cấu trúc |
| RC04 | Khơi gợi mong muốn | Cho thấy tương lai khả thi và cây cầu thay đổi |
| RC05 | Giới thiệu giải pháp | Giải thích giải pháp trước khi nhấn thương hiệu |
| RC06 | Giải thích tính năng – lợi ích | Nối đặc điểm với giá trị trong bối cảnh sử dụng |
| RC07 | Thiết lập tiêu chí lựa chọn | Trao quyền quyết định thay vì chỉ tự khen |
| RC08 | So sánh phương án | Dùng cùng tiêu chí và thừa nhận đánh đổi |
| RC09 | Xây dựng niềm tin | Chứng minh đúng luận điểm bằng nguồn liên quan |
| RC10 | Xử lý phản đối | Đồng cảm trước, trả lời trực tiếp, đưa bước ít rủi ro |
| RC11 | Tạo kiểm chứng | Cho người xem tự quan sát giá trị |
| RC12 | Thúc đẩy chuyển đổi | Minh bạch đề nghị, proof và điều kiện |
| RC13 | Onboarding | Giảm bối rối và tạo thành công sớm |
| RC14 | Tăng hiệu quả sử dụng | Giúp người dùng nhận nhiều giá trị hơn |
| RC15 | Chứng minh tiến bộ | Cho thấy quá trình và điều kiện, không chỉ kết quả |
| RC16 | Duy trì và trung thành | Kết hợp giá trị lặp lại và cảm giác thuộc về |
| RC17 | Lan tỏa và referral | Giảm rào cản và ghi nhận người tham gia |
| RC18 | Định vị thương hiệu | Lập trường phải được hành vi thực tế chứng minh |
| RC19 | Văn hóa và con người | Tập trung hành vi và tiêu chuẩn thay vì khẩu hiệu |
| RC20 | PR thành tựu / cột mốc | Giải thích ý nghĩa thực thay vì chỉ liệt kê danh hiệu |
| RC21 | Dẫn dắt xu hướng | Ghi rõ nguồn, thời điểm và mức chắc chắn |
| RC22 | Cộng đồng và bản sắc | Tạo quyền tham gia thật và không loại trừ |
| RC23 | Đối thoại và lắng nghe | Đóng vòng phản hồi: cho biết ý kiến được dùng thế nào |
| RC24 | Tác động xã hội | Đo tác động thật và tránh purpose-washing |

Cột "nguyên tắc cốt lõi" là **ràng buộc biên tập**, không phải mô tả suông.
RC09 chọn tổ hợp bằng chứng nhưng nếu bằng chứng không liên quan tới luận điểm
thì tổ hợp đó phải bị trừ điểm feasibility.

## 6. Ngữ nghĩa 9 quan hệ

Từ vựng công bố gồm 9 quan hệ. **Chỉ 3 quan hệ đầu có cạnh thực trong dữ liệu
v2.0.0** — xem `source-provenance.md`.

| Quan hệ | Hướng | Ý nghĩa | Trạng thái v2.0.0 |
|---|---|---|---|
| `CONTAINS` | cha → con | Phân cấp MP→Pillar, Pillar→Angle | **696 cạnh** |
| `BELONGS_TO` | con → cha | Nghịch đảo của CONTAINS | **696 cạnh** |
| `COMPATIBLE_WITH` | vô hướng | Hai node phối hợp được, kèm trọng số 0.40–1.00 | **68.328 cạnh** |
| `RECOMMENDED_FOR` | node → goal/stage | Khuyến nghị cho mục tiêu hoặc giai đoạn | 0 cạnh |
| `AMPLIFIES` | node → node | Node A khuếch đại hiệu lực của B | 0 cạnh |
| `EXPRESSED_AS` | angle → headline | Góc nhìn được diễn đạt thành tiêu đề | 0 cạnh |
| `DELIVERED_AS` | ý tưởng → content type | Ý tưởng được chuyển giao qua định dạng | 0 cạnh |
| `AVOID_WITH` | vô hướng | Hai node xung khắc, cần loại hoặc phạt nặng | 0 cạnh |
| `PRIORITIZED_BY` | node → goal | Node được ưu tiên bởi mục tiêu | 0 cạnh |

Khi 6 quan hệ còn lại được website bổ sung, `sync_matrixcontent.py` nạp chúng
tự động vào `graph-index.json` và `select_combinations.py` dùng ngay mà không
cần sửa code — engine đọc quan hệ theo tên, không hardcode ba loại.

## 7. Cấu trúc cạnh và trọng số

```json
{
  "source": "CJ01-A01",
  "target": "CF01",
  "relation": "COMPATIBLE_WITH",
  "weight": 0.88,
  "reason": "Khoảnh khắc nhận ra vấn đề tương thích với AIDA",
  "origin": "rule-derived"
}
```

- `weight` ∈ [0.40, 1.00]. Phân bố tập trung 0.55–0.75. Vì vậy **0.88 là cao
  thật sự**, còn 0.45 gần như là mức sàn — đừng đọc 0.45 như "trung bình".
- `origin`: `source` (1.392 cạnh phân cấp, trích từ tài liệu gốc) ·
  `rule-derived` (68.328 cạnh tương thích, sinh bằng luật) · `manual` (chưa có).
- `reason` của cạnh `rule-derived` theo khuôn "X tương thích với Y" — **không
  trích dẫn nó như lý lẽ biên tập**. Lý do chọn tổ hợp phải do bạn lập luận.

Độ phủ cạnh từ mỗi Content Angle (đủ dày để luôn có lựa chọn):

| Đích | Ít nhất | Nhiều nhất | Trung bình |
|---|---|---|---|
| ContentFormula | 10 | 23 | 15,4 |
| SuccessPattern | 20 | 27 | 23,2 |
| HeadlineTemplate | 30 | 37 | 33,6 |
| ContentType | 15 | 27 | 20,9 |

Không Content Angle nào thiếu cạnh tới bất kỳ loại nào.

## 8. Mười cặp trong một tổ hợp 5 điểm

Đây là điểm mạnh thật sự của đồ thị: mọi cặp trong tổ hợp đều có cạnh
`COMPATIBLE_WITH` riêng, nên tính nhất quán đo được chứ không phải cảm tính.

```
Angle→CF   Angle→SP   Angle→HT   Angle→CT        (4 cạnh, gốc từ Angle)
CF→SP      CF→HT      CF→CT                      (3 cạnh chéo)
SP→HT      SP→CT                                 (2 cạnh chéo)
HT→CT                                            (1 cạnh chéo)
```

Tổng 10 cạnh. `select_combinations.py` lấy trung bình có trọng số của 10 giá
trị này làm **điểm nhất quán** (20 điểm trong rubric). Cạnh vắng mặt tính là
0.35 (dưới sàn) và bị ghi nhận `missing_edges` — nhiều cạnh vắng nghĩa là tổ
hợp bị ép, nên rớt hạng.

Ma trận có sẵn (số cạnh): SP–HT 2.503 · HT–CT 2.262 · CF–HT 1.686 ·
SP–CT 1.578 · CF–SP 1.148 · CF–CT 1.065.

## 9. Từ vựng tag

Tag là dữ liệu thật, dùng cho cả matching lẫn đo đa dạng.

- **ContentFormula** — 40 tag, gần như mỗi công thức một tag riêng
  (Thuyết phục và chuyển đổi, Vấn đề và giải pháp, Kể chuyện, So sánh và lựa chọn,
  Case study, Xử lý phản đối, Hỏi đáp, Bán hàng dài…). Tag CF gần như là ID —
  **không dùng để đo đa dạng**.
- **SuccessPattern** — 22 tag, phân bố rộng: Chuyển đổi (9), Tương tác (8),
  Tự sự (5), Bằng chứng (5), Hữu ích (5), Giáo dục (5), Thời sự (4), Chú ý (4),
  Cảm xúc (4), Minh bạch, Trải nghiệm, Cân nhắc, Bản sắc… **Đây là trục đo
  "trạng thái tâm lý" tốt nhất.**
- **HeadlineTemplate** — đúng 16 tag × 6 mẫu: Lợi ích và kết quả · How-to và
  hướng dẫn · Danh sách và con số · Vấn đề và cảnh báo · Sai lầm và điều cần tránh ·
  Câu hỏi và tự chẩn đoán · Tò mò và tiết lộ · Bằng chứng và dữ liệu ·
  Chuyên gia và thẩm quyền · So sánh và lựa chọn · Myth và góc nhìn ngược ·
  Câu chuyện và chuyển đổi · Đối tượng và bản sắc · Thời điểm, xu hướng và tin mới ·
  Offer và hành động · Minh bạch và hậu trường.
- **ContentType** — 16 tag theo phương tiện: Văn bản (14), Video (11), Hình ảnh (9),
  Tương tác (5), Trực tiếp (4), Email (3), Audio, PR, Cộng đồng, Sự kiện…

`ContentType.suitable_channels` là **trường kênh duy nhất có dữ liệu thật**
trong toàn hệ thống. Từ vựng kênh không được chuẩn hóa (`Social`/`social`/
`Social feed`/`social clips` cùng tồn tại) — chuẩn hóa bằng `channel_aliases`
trong `data/semantic-overlay.json`.

## 10. Cách chọn Master Pillar

Không chọn theo từ khóa. Hỏi theo thứ tự:

1. **Khách hàng đã biết mình có vấn đề chưa?** Chưa → MP01 (CJ01–CJ06) hoặc
   MP04 (JT02–JT03). Rồi → bỏ qua tầng nhận biết.
2. **Rào cản là thiếu tin hay thiếu hiểu?** Thiếu tin → MP02 (BR08, BR14, BR15)
   + MP01 (CJ09–CJ11). Thiếu hiểu → MP04 (JT08) hoặc MP01 (CJ05).
3. **Rào cản nằm ở giá, kênh mua, quy trình, con người?** → MP03 (MM02, MM03,
   MM05, MM06).
4. **Mục tiêu là giữ chân, gắn bó, lan tỏa, bản sắc?** → MP05.
5. **Thương hiệu cần được nhớ vì điều gì?** → MP02.

Một brief tốt thường trải trên **2–3 Master Pillar**. Danh sách 10 hướng nên
phản ánh điều đó thay vì dồn hết vào một pillar — đó là nguồn đa dạng rẻ nhất
và đúng chiến lược nhất.
