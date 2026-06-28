# Kiến trúc ModClear

## Tổng quan

ModClear là một Intelligent Contract đơn lẻ quản lý vòng đời kháng nghị kiểm duyệt nội dung, cộng một frontend tĩnh gọi vào nó qua `genlayer-js`. Toàn bộ phán quyết xảy ra **on-chain** thông qua bồi thẩm đoàn AI của GenLayer.

## Mô hình dữ liệu

```
Contract
├── appeals: TreeMap[u256, Appeal]
├── next_id: u256
├── owner: Address
└── treasury: u256              # phí thu từ các kháng nghị thất bại

Appeal
├── creator: Address
├── platform: str               # "YouTube", "TikTok"...
├── action_type: str            # REMOVAL | DEMONETIZATION | STRIKE | AGE_RESTRICT
├── content_url: str            # nội dung bị xử lý
├── policy_url: str             # trang chính sách bị viện dẫn
├── policy_quote: str           # trích đoạn điều khoản
├── creator_statement: str      # lập luận creator
├── fee: u256                   # phí ký quỹ
├── status: str                 # FILED | REVIEWING | RESOLVED | CLOSED
├── ruling: str                 # UPHELD | OVERTURNED | PARTIAL
├── confidence: u256            # 0..100
├── rationale: str              # lý do AI
└── fee_refunded: bool
```

## State machine

```
        file_appeal (payable)
              │
              ▼
          ┌───────┐
          │ FILED │
          └───┬───┘
              │ adjudicate()
              ▼
        ┌───────────┐
        │ REVIEWING │   (chuyển trạng thái trước khi gọi AI Jury)
        └─────┬─────┘
              │ run_nondet_unsafe → đồng thuận
              ▼
        ┌──────────┐
        │ RESOLVED │  ruling + confidence + rationale ghi on-chain
        └────┬─────┘
             │ settle_fee()
             ▼
        ┌────────┐
        │ CLOSED │  OVERTURNED/PARTIAL→hoàn phí; UPHELD→treasury
        └────────┘
```

## Luồng đồng thuận của `adjudicate()`

### Leader function
1. `gl.nondet.web.render(content_url)` và `gl.nondet.web.render(policy_url)`; bắt lỗi link chết thành `[UNREACHABLE]`.
2. Dựng prompt nêu rõ **nguyên tắc xử**: chỉ xét theo điều khoản được viện dẫn, hẹp; gánh nặng chứng minh thuộc về bên thực thi; "khó chịu" ≠ "vi phạm"; nếu mơ hồ hoặc không đọc được → nghiêng về OVERTURNED (lợi cho creator).
3. `gl.nondet.exec_prompt(..., response_format="json")` → `{ruling, confidence, rationale}`.

### Validator function — kiểm Ý NGHĨA, không kiểm hình dạng
1. Kiểm `gl.vm.Return` + parse JSON + ruling/confidence hợp lệ.
2. Đọc lại nội dung + chính sách, chạy LLM riêng để ra **ruling độc lập**.
3. **Từ chối** nếu leader và validator ra hai cực đối nghịch (UPHELD vs OVERTURNED). PARTIAL tương thích với cả hai phía.

→ Hai validator có thể khác nhau về câu chữ nhưng vẫn đồng thuận nếu cùng kết luận creator thắng/thua; phán quyết "đúng schema nhưng trái bản chất" bị loại.

## Xử lý edge-case

| Tình huống | Xử lý |
|---|---|
| Link nội dung/chính sách chết | `[UNREACHABLE]`, AI nghiêng về OVERTURNED |
| LLM trả JSON hỏng | `validator_fn` từ chối → không đồng thuận sai |
| ruling lạ / confidence ngoài [0,100] | bị từ chối / kẹp lại |
| fee = 0 | `file_appeal` raise lỗi |
| action_type không hợp lệ | `file_appeal` raise lỗi |
| settle_fee 2 lần | chặn bằng cờ `fee_refunded` |
| rút treasury trái phép | chỉ `owner` |
| send thất bại | dùng `send_value` ở bước settle riêng, không trộn vào adjudicate |

## Hướng mở rộng (milestone tương lai)

- **Appeal vòng 2**: bên thua stake để kháng nghị lại, jury mở rộng.
- **Reputation**: chấm điểm nền tảng theo tỷ lệ bị OVERTURNED — minh bạch hoá độ "lạm quyền".
- **Multi-source**: cross-check nhiều bản chính sách theo thời điểm (Wayback Machine) để xử đúng phiên bản policy tại thời điểm bị xử lý.
- **Tách multi-contract**: Registry chính sách + Treasury + Appeals.
