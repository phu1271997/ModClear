# ModClear — Toà phúc thẩm kiểm duyệt nội dung phi tập trung

> Một **Intelligent Contract** trên GenLayer biến mỗi kháng nghị kiểm duyệt thành một phán quyết AI on-chain: validators đọc thẳng **cả nội dung bị xử lý lẫn trang chính sách công khai**, rồi phán độc lập với nền tảng — **UPHELD (giữ nguyên) / OVERTURNED (gỡ oan) / PARTIAL (một phần)** — công khai và bất biến.

---

## 1. Bài toán

Creator bị nền tảng (YouTube, TikTok, X...) **gỡ video, tắt kiếm tiền (demonetize), hoặc nhận strike** — nhiều khi sai. Cơ chế kháng nghị của chính nền tảng là một **hố đen**: chậm, mờ ám, và do chính bên ra quyết định tự xử lại. Creator mất thu nhập mà không có toà trung lập nào xét lại độc lập.

Câu hỏi cốt lõi — *"nội dung này có thực sự vi phạm chính điều khoản được viện dẫn không?"* — là một **phán quyết chủ quan** dựa trên dữ liệu phi cấu trúc.

## 2. Vì sao dự án này CHẾT nếu không có GenLayer

Phán quyết đòi hỏi hai thứ **Solidity không bao giờ làm được**:

1. **Đọc dữ liệu web phi cấu trúc on-chain** — cả nội dung bị xử lý lẫn trang chính sách công khai, qua `gl.nondet.web.render`, không oracle, không trung gian.
2. **Suy luận chủ quan có ngữ cảnh** — đối chiếu nội dung với một điều khoản diễn đạt bằng ngôn ngữ tự nhiên và phán "có vi phạm hay không" là phán đoán kiểu con người. LLM tại tầng đồng thuận của GenLayer biến nó thành kết quả thực thi được trên chuỗi.

Bỏ phần AI + web đi thì không còn sản phẩm — không smart contract truyền thống nào "đọc" được một video và một trang guidelines rồi ra phán quyết. **AI là trái tim, không phải gia vị.**

Điểm độc đáo: ModClear tạo ra thứ mà **các nền tảng tập trung không bao giờ tự xây** — một toà phúc thẩm trung lập, công khai, bất biến, đứng ngoài lợi ích của nền tảng.

## 3. Kiến trúc

```
┌─────────────┐   genlayer-js    ┌────────────────────────┐
│  Frontend   │ ───────────────▶ │  ModClear (Python IC)  │
│ (index.html)│ ◀─────────────── │     trên GenLayer      │
└─────────────┘   đọc state      └──────────┬─────────────┘
                                            │ adjudicate()
                                            ▼
                            ┌────────────────────────────────┐
                            │  AI Jury (validators)           │
                            │  • web.render(nội dung)         │
                            │  • web.render(chính sách)       │
                            │  • LLM: vi phạm điều khoản?      │
                            │  • validator_fn kiểm Ý NGHĨA     │
                            └────────────────────────────────┘
```

**Vòng đời một kháng nghị (state machine):**

```
file_appeal(payable) ──▶ FILED ──adjudicate──▶ REVIEWING ──▶ RESOLVED
                                                                │ settle_fee
                                                                ▼
                                                             CLOSED
```

### Điểm nhấn về chất lượng đồng thuận

`validator_fn` **không** chỉ kiểm JSON đúng schema. Nó:
- Kiểm `ruling ∈ {UPHELD, OVERTURNED, PARTIAL}` và `confidence ∈ [0,100]`.
- Chạy lại LLM của chính validator, đọc lại cả nội dung lẫn chính sách, ra ruling độc lập.
- **Từ chối** khi leader và validator ra hai kết luận **trái ngược** (UPHELD vs OVERTURNED). PARTIAL được coi là tương thích với cả hai phía (phán quyết trung gian), nhưng hai cực đối nghịch thì không được đồng thuận.

Nghĩa là hai validator diễn đạt lý do khác nhau vẫn đồng thuận nếu **cùng kết luận creator thắng hay thua**; còn "đúng định dạng nhưng trái ngược bản chất" thì bị loại. Đây là ranh giới chất lượng mà chương trình chấm điểm yêu cầu.

## 4. Cấu trúc thư mục

```
ModClear/
├── contracts/
│   ├── mod_clear.py         # Intelligent Contract chính
│   └── storage_test.py      # contract sanity, deploy trước
├── frontend/
│   ├── index.html           # dApp single-file qua genlayer-js
│   └── src/config.js
├── tests/test_mod_clear.py
├── scripts/deploy.sh
├── docs/{ARCHITECTURE.md, COMMON_ERRORS.md, samples/SCENARIOS.md}
├── CHANGELOG.md
└── README.md
```

## 5. Deploy lên testnet — từng bước

### Chuẩn bị
1. `npm install -g genlayer`
2. Lấy testnet GEN: https://www.genlayer.com/testnet
3. `genlayer keygen` (hoặc import ví)

### Cách A — Qua GenLayer Studio (nhanh nhất để demo)
1. Mở https://studio.genlayer.com/run-debug
2. **Settings → Reset Storage → Confirm**, hard refresh (Cmd/Ctrl+Shift+R).
3. Deploy `contracts/storage_test.py` trước → xác nhận `Result: SUCCESS`.
4. Deploy `contracts/mod_clear.py`.
5. Copy địa chỉ → dán vào `frontend/src/config.js` (`CONTRACT_ADDRESS`), đặt `CHAIN = "studio"`.

### Cách B — Qua CLI
```bash
cd ModClear
bash scripts/deploy.sh testnet-asimov   # hoặc 'localnet'
```

## 6. Chạy frontend

```bash
cd ModClear/frontend
npx serve .        # hoặc: python3 -m http.server 8000
```
Mở trình duyệt → **Kết nối ví** → 3 bước: Nộp kháng nghị → Triệu tập AI Jury → Tra cứu phán quyết. Deploy live trỏ thẳng vào `frontend/` (nhớ cập nhật `src/config.js`).

## 7. Luồng demo end-to-end

1. **Creator** nộp kháng nghị: link video bị demonetize + link guidelines + trích đoạn điều khoản bị viện dẫn + lập luận. Ký quỹ phí `5000`.
2. **Triệu tập AI Jury** → validators đọc cả nội dung lẫn chính sách, phán độc lập.
3. Phán quyết hiện ra: ví dụ `OVERTURNED`, confidence `82/100`, kèm lý do bằng tiếng người.
4. **Giải quyết phí**: OVERTURNED/PARTIAL → hoàn phí creator; UPHELD → vào treasury.

Xem 3 kịch bản trong `docs/samples/SCENARIOS.md`.

## 8. Test

```bash
gltest tests/test_mod_clear.py
```
Phủ state machine, phân quyền, validate input (fee = 0, action_type sai, URL rỗng), và bất biến giải quyết phí theo phán quyết.

## 9. Tài liệu thêm

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/COMMON_ERRORS.md`](docs/COMMON_ERRORS.md) — 7+1 rule tránh lỗi deploy GenLayer.

---

*ModClear được xây cho GenLayer testnet Bradbury. GenLayer đang ở giai đoạn testnet — chi tiết mạng có thể thay đổi; kiểm chứng tại docs.genlayer.com trước khi deploy.*
