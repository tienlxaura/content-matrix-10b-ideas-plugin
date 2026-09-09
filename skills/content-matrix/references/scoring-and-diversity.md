# Chấm điểm và đa dạng hóa

## Mục lục
1. [Rubric 100 điểm](#1-rubric-100-điểm)
2. [Hình phạt](#2-hình-phạt)
3. [Ngưỡng đa dạng](#3-ngưỡng-đa-dạng)
4. [MMR — chọn danh sách cuối](#4-mmr--chọn-danh-sách-cuối)
5. [Đọc điểm số](#5-đọc-điểm-số)
6. [Chọn Top 3](#6-chọn-top-3)
7. [Rubric dùng cho chế độ đánh giá nội dung có sẵn](#7-rubric-dùng-cho-chế-độ-đánh-giá-nội-dung-có-sẵn)

---

## 1. Rubric 100 điểm

| # | Tiêu chí | Điểm | Nguồn tín hiệu |
|---|---|---|---|
| 1 | Phù hợp brief và đối tượng | 20 | khớp ngữ nghĩa Angle/Pillar với topic, audience, insight, industry |
| 2 | Phù hợp mục tiêu marketing | 15 | goal affinity (**semantic overlay**) + khớp pillar theo bảng giai đoạn |
| 3 | Tính nhất quán giữa 5 điểm | 20 | **10 cạnh `COMPATIBLE_WITH` thật** trong đồ thị |
| 4 | Insight và giá trị cho người đọc | 15 | độ sâu `direction` của Angle + `mechanism` của SP + khớp insight |
| 5 | Tính mới và khả năng tạo chú ý | 10 | độ hiếm của tổ hợp + tag SP thuộc nhóm Chú ý/Cảm xúc/Myth + nghịch đảo tần suất |
| 6 | Phù hợp kênh và Content Type | 10 | `suitable_channels` **(dữ liệu thật)** + `format_specs` + `content_type_hint` |
| 7 | Khả năng triển khai, bằng chứng, độ tin cậy | 10 | `complexity` của 5 node + `assets` trong brief + nhu cầu bằng chứng của SP/CF |

Tiêu chí 3 là tiêu chí duy nhất **hoàn toàn** dựa trên dữ liệu gốc của website.
Tiêu chí 6 dựa một phần. Tiêu chí 2 là **semantic fallback toàn phần** — phải
ghi rõ khi trình bày.

Công thức tiêu chí 3:

```
coherence_raw = Σ(w_i × k_i) / Σ(k_i)     với 10 cạnh
k = 1.5 cho 4 cạnh gốc từ Angle, 1.0 cho 6 cạnh chéo
w của cạnh vắng mặt = 0.35
điểm_3 = normalize(coherence_raw, sàn 0.40, trần 0.95) × 20
```

Chuẩn hóa theo sàn 0.40 / trần 0.95 là bắt buộc: trọng số thô tập trung ở
0.55–0.75, nếu nhân thẳng thì mọi tổ hợp đều ra 11–15/20 và tiêu chí này mất
khả năng phân biệt.

## 2. Hình phạt

Trừ **sau** khi cộng rubric:

| Hình phạt | Mức | Kích hoạt khi |
|---|---|---|
| `avoid_violation` | −25, loại khỏi danh sách | cặp nằm trong `AVOID_WITH` thật hoặc `avoid_rules` của overlay |
| `capacity_penalty` | −3 … −12 | số bước Content Formula vượt sức chứa Content Type |
| `missing_edge_penalty` | −1,5 mỗi cạnh vắng | tối đa −9 |
| `evidence_gap` | −8 | tổ hợp đòi bằng chứng (SP tag Bằng chứng / CF Case study) nhưng `assets` rỗng |
| `constraint_violation` | −20, loại | vi phạm `constraints` hoặc `avoid` trong brief |
| `redundancy_penalty` | −0 … −15 | trùng lặp với các hướng đã chọn trước đó (tính trong MMR) |

Điểm cuối:

```
final = clamp(Σ rubric − Σ penalties, 0, 100)
```

Tổ hợp bị `avoid_violation` hoặc `constraint_violation` **không** xuất hiện
trong 10 hướng, kể cả khi rubric cao.

## 3. Ngưỡng đa dạng

Ràng buộc cặp (bắt buộc, không có ngoại lệ):

> Với mọi cặp hướng (i, j): số thành phần khác nhau trong
> {Angle, Formula, SuccessPattern, HeadlineTemplate, ContentType} **≥ 2**.

Ràng buộc danh sách, khi brief **không** khóa cứng bằng `*_hint`:

| Trục | Tối thiểu trong 10 hướng |
|---|---|
| Content Angle khác nhau | 4 |
| Success Pattern khác nhau | 4 |
| Content Type khác nhau | 3 |
| **tag** Success Pattern khác nhau | 4 (proxy của "trạng thái tâm lý") |
| Pillar khác nhau | 3 |

Khi brief khóa cứng (ví dụ chỉ định 1 Angle), các ngưỡng danh sách giảm theo tỉ
lệ và **phải nói rõ** trong phần giả định rằng đa dạng bị giới hạn bởi brief.

Trục "trạng thái tâm lý" dùng tag SuccessPattern (22 tag: Chú ý, Cảm xúc, Tự sự,
Bằng chứng, Hữu ích, Giáo dục, Thời sự, Chuyển đổi, Tương tác, Minh bạch,
Bản sắc, Cân nhắc…). Không dùng tag ContentFormula — mỗi công thức gần như một
tag riêng nên trục đó luôn "đa dạng" một cách giả tạo.

## 4. MMR — chọn danh sách cuối

Maximal Marginal Relevance, λ mặc định 0,65 (`--diversity 0.35`):

```
MMR(c) = λ × norm(final_score(c)) − (1−λ) × max_similarity(c, đã_chọn)
```

Độ tương đồng giữa hai tổ hợp:

```
sim = 0.30·[cùng Angle] + 0.15·[cùng Pillar] + 0.20·[cùng SuccessPattern]
    + 0.10·[cùng tag SP] + 0.15·[cùng ContentFormula]
    + 0.05·[cùng HeadlineTemplate] + 0.05·[cùng ContentType]
```

Vòng lặp: chọn tổ hợp điểm cao nhất trước, sau đó mỗi vòng chọn tổ hợp có MMR
cao nhất **và** thỏa ràng buộc ≥2/5. Nếu không còn ứng viên thỏa ràng buộc, nới
λ dần 0,05 mỗi lần thay vì phá ràng buộc ≥2/5.

Sau khi có 10 hướng, kiểm tra ngưỡng danh sách §3. Thiếu trục nào thì thay hướng
xếp cuối bằng ứng viên tốt nhất bổ sung được trục đó.

## 5. Đọc điểm số

Thang là 100 điểm, nhưng **thực tế không tổ hợp nào đạt tối đa mọi tiêu chí
cùng lúc** — một tổ hợp mới lạ thì khó triển khai, một tổ hợp an toàn thì kém
mới. Trên 5 eval case, điểm quan sát được nằm trong khoảng **46–73**. Đọc theo
thang thực tế đó:

| Khoảng | Ý nghĩa |
|---|---|
| ≥ 68 | Rất mạnh, ưu tiên hàng đầu |
| 60–67 | Mạnh, triển khai được, có thể cần bổ sung bằng chứng |
| 52–59 | Khả thi nhưng có đánh đổi rõ, phải nêu rủi ro |
| < 52 | Chỉ giữ nếu cần lấp trục đa dạng, phải ghi rõ điểm yếu |

Brief càng mỏng thì trần điểm càng thấp — đó là hành vi đúng, không phải lỗi.
Một brief chỉ có chủ đề thường cho toàn bộ danh sách dưới 60.

Điểm không phải là sự thật khách quan. Nó là **thứ tự ưu tiên có thể tranh
luận**. Nếu bạn thấy hướng hạng 6 mạnh hơn hạng 2 về mặt chiến lược, hãy nói ra
và giải thích, đừng im lặng theo số.

**Bắt buộc kiểm tra thủ công trước khi trình bày:** engine khớp brief với
catalog bằng từ vựng, mà catalog cố tình phi ngành. Tiếng Việt lại có nhiều từ
ghép trùng nhau giữa các ngành ("nội dung **nổi bật**" của một bản tổng kết
chiến dịch trùng với "con **nổi bật**" trong insight của phụ huynh). Vì vậy một
hướng xếp hạng cao vẫn có thể lệch ngành hoặc lệch đối tượng.

Với mỗi hướng, tự hỏi: *Content Angle này có nói với đúng người mà brief nhắm
tới không?* Nếu không — loại nó, ghi rõ lý do, và lấy hướng kế tiếp trong danh
sách. Đây là lỗi duy nhất mà engine không tự phát hiện được.

## 6. Chọn Top 3

Không lấy đơn thuần 3 điểm cao nhất. Top 3 phải:

1. Phủ **ít nhất 2 Master Pillar** khác nhau.
2. Có **ít nhất 1 hướng triển khai được ngay** với `assets` hiện có.
3. Không cùng một Success Pattern.
4. Cùng nhau tạo thành một chuỗi dùng được (mở đầu → củng cố → chuyển đổi),
   không phải ba biến thể của một ý.

Giải thích lý do chọn bằng ngôn ngữ chiến lược: hướng này giải quyết rào cản
nào, ở giai đoạn nào, đo bằng gì. Không lặp lại điểm số.

## 7. Rubric dùng cho chế độ đánh giá nội dung có sẵn

Cùng 7 tiêu chí, nhưng tín hiệu lấy từ chính nội dung:

| Tiêu chí | Cách chấm khi đọc bài có sẵn |
|---|---|
| 1 Phù hợp brief/đối tượng | Bài nói với ai? Có xưng hô, ví dụ, mối bận tâm đúng nhóm không? |
| 2 Phù hợp mục tiêu | CTA và mạch bài có phục vụ đúng goal không, hay lệch sang goal khác? |
| 3 Nhất quán 5 điểm | Suy ngược 5 điểm đang dùng, kiểm tra 10 cạnh thật trong đồ thị |
| 4 Insight | Có điều gì người đọc chưa tự nghĩ ra không? Hay chỉ nói lại điều hiển nhiên? |
| 5 Tính mới | Hook có bị mòn không? Bao nhiêu brand cùng ngành viết được y hệt? |
| 6 Kênh/định dạng | Độ dài, nhịp, cấu trúc có đúng kênh không? |
| 7 Triển khai/tin cậy | Có tuyên bố nào thiếu bằng chứng? Có cam kết vượt phép không? |

Luôn chỉ ra **điểm yếu cụ thể kèm trích dẫn câu trong bài**, không phê bình
chung chung.
