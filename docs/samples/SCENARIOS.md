# Kịch bản mẫu để demo ModClear

Ba kịch bản dựng sẵn, mỗi cái minh hoạ một loại phán quyết. Dùng để quay video
demo hoặc seed dữ liệu cho contract không trống.

> Mẹo: tạo các trang đơn giản (một file HTML mô tả nội dung video + một file HTML
> là trích policy) host trên GitHub Pages / IPFS / URL công khai bất kỳ đọc được,
> rồi dán link vào contract. AI sẽ render text và đọc.

---

## Kịch bản 1 — OVERTURNED (gỡ oan)

Nền tảng demonetize sai; nội dung không vi phạm điều khoản được viện dẫn.

- **Platform:** YouTube · **Action:** DEMONETIZATION · **Fee:** 5000
- **Content page:** mô tả một video phân tích học thuật về lịch sử xung đột, giọng trung lập, không cổ vũ bạo lực, không hình ảnh gây sốc.
- **Policy page:** điều khoản "nội dung tôn vinh hoặc kích động bạo lực sẽ bị tắt kiếm tiền".
- **Policy quote:** "Content that glorifies or incites violence will be demonetized."
- **Creator statement:** "Video chỉ phân tích bối cảnh lịch sử, không tôn vinh hay kích động bất kỳ hành vi bạo lực nào."
- **Phán quyết kỳ vọng:** `OVERTURNED`, confidence cao. Lý do: phân tích học thuật trung lập không rơi vào "tôn vinh/kích động" theo đúng điều khoản.

---

## Kịch bản 2 — UPHELD (giữ nguyên)

Nội dung thực sự vi phạm chính điều khoản được viện dẫn.

- **Platform:** TikTok · **Action:** REMOVAL · **Fee:** 5000
- **Content page:** mô tả video hướng dẫn cách chế tạo một thiết bị nguy hiểm, có bước cụ thể.
- **Policy page:** điều khoản "nội dung hướng dẫn chế tạo vũ khí/thiết bị nguy hiểm bị cấm và sẽ bị gỡ".
- **Policy quote:** "Content providing instructions to build dangerous devices is prohibited and will be removed."
- **Creator statement:** "Tôi cho rằng đây chỉ là nội dung giáo dục."
- **Phán quyết kỳ vọng:** `UPHELD`, confidence cao. Lý do: nội dung khớp trực tiếp với điều khoản cấm; "giáo dục" không miễn trừ phần hướng dẫn cụ thể.

---

## Kịch bản 3 — PARTIAL (một phần / xử lý quá nặng)

Có vi phạm nhẹ nhưng hình thức xử lý không tương xứng.

- **Platform:** YouTube · **Action:** STRIKE · **Fee:** 5000
- **Content page:** mô tả video chủ yếu hợp lệ, nhưng có một đoạn ngắn dùng ngôn từ thô tục không đính nhãn.
- **Policy page:** điều khoản phân tầng: ngôn từ thô tục nhẹ → cảnh báo/age-restrict; nội dung thù ghét nghiêm trọng → strike/gỡ.
- **Policy quote:** "Severe hateful content results in a strike; mild profanity may be age-restricted."
- **Creator statement:** "Có chút ngôn từ mạnh nhưng không phải nội dung thù ghét, một strike là quá nặng."
- **Phán quyết kỳ vọng:** `PARTIAL`. Lý do: có vi phạm nhẹ (đáng age-restrict) nhưng STRIKE là không tương xứng theo chính chính sách phân tầng.

---

## Cách chạy nhanh trên Studio

1. Deploy `mod_clear.py`.
2. `file_appeal(platform, action_type, content_url, policy_url, policy_quote, creator_statement)` kèm `value = 5000`.
3. `adjudicate(0)` → chờ đồng thuận.
4. `get_appeal(0)` → đọc ruling + confidence + rationale.
5. `settle_fee(0)` → hoàn phí hoặc thu vào treasury theo phán quyết.
