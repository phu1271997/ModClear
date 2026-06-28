# Changelog

Theo [Semantic Versioning](https://semver.org/).

## [1.0.0] — Bản phát hành đầu

### Added
- Intelligent Contract `mod_clear.py`: vòng đời kháng nghị kiểm duyệt đầy đủ (FILED → REVIEWING → RESOLVED → CLOSED).
- AI Jury qua `gl.vm.run_nondet_unsafe`: đọc cả nội dung lẫn chính sách trên web on-chain, phán độc lập UPHELD/OVERTURNED/PARTIAL kèm confidence + rationale.
- `validator_fn` kiểm **ý nghĩa** phán quyết (đọc lại độc lập, từ chối khi hai cực đối nghịch), không chỉ kiểm schema.
- Cơ chế phí ký quỹ chống spam: hoàn cho creator nếu thắng (OVERTURNED/PARTIAL), vào treasury nếu thua (UPHELD).
- Frontend single-file gọi thật qua `genlayer-js`: 3 bước trọn luồng, loading state khi chờ consensus, hiển thị ruling + confidence + lý do AI.
- Bộ test `tests/test_mod_clear.py`: happy path + edge cases + bất biến giải quyết phí.
- `contracts/storage_test.py`: contract sanity deploy trước.
- Tài liệu: README, ARCHITECTURE.md, COMMON_ERRORS.md, 3 kịch bản demo.

### Security
- Validate input chặt: fee > 0, action_type trong tập hợp lệ, URL không rỗng.
- Chặn settle_fee hai lần bằng cờ `fee_refunded`.
- Phân quyền: chỉ owner rút treasury, kiểm số dư trước khi gửi.
- TreeMap safe read (kiểm tồn tại trước khi truy cập).
