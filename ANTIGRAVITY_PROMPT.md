# PROJECT CONTEXT PROMPT — ModClear (cho Antigravity IDE)

> Dán toàn bộ nội dung này vào Antigravity (hoặc bất kỳ AI IDE nào) để agent
> hiểu ngay dự án là gì, kiến trúc ra sao, và các ràng buộc kỹ thuật sống còn
> khi sửa/mở rộng code. Mục tiêu: agent không phá vỡ quy tắc GenLayer và giữ
> đúng định hướng "đạt điểm unicorn 4–5".

---

## 1. Dự án này là gì

**ModClear** là một **Intelligent Contract** trên **GenLayer** (blockchain L1
đặt AI ở tầng đồng thuận; contract viết bằng Python; chạy được tác vụ
non-deterministic như gọi LLM và đọc web on-chain).

**Bài toán:** **toà phúc thẩm trung lập cho kiểm duyệt nội dung.** Creator bị
nền tảng (YouTube, TikTok, X...) gỡ video / demonetize / strike sai, nhưng cơ
chế kháng nghị của nền tảng là hố đen — chậm, mờ ám, do chính bên ra quyết định
tự xử lại. Câu hỏi cốt lõi "nội dung này có thực sự vi phạm chính điều khoản
được viện dẫn không" là một **phán quyết chủ quan** trên dữ liệu phi cấu trúc.

**Cách giải:** mỗi kháng nghị thành một **phán quyết AI on-chain**. Validators
tự `gl.nondet.web.render` đọc thẳng cả nội dung bị xử lý lẫn trang chính sách
công khai, dùng LLM phán độc lập với nền tảng → **UPHELD (giữ nguyên) /
OVERTURNED (gỡ oan) / PARTIAL (một phần)** kèm confidence + lý do. Phán quyết
ghi on-chain, công khai, bất biến. Phí ký quỹ chống spam: hoàn nếu thắng, vào
treasury nếu thua.

## 2. Vì sao dự án CHẾT nếu không có GenLayer (one-line pitch)

> "Không smart contract truyền thống nào đọc nổi một video và một trang
> guidelines rồi phán 'có vi phạm điều khoản này không' — phán quyết chủ quan
> trên dữ liệu web phi cấu trúc là thứ chỉ GenLayer làm được, và nó chính là
> toàn bộ sản phẩm. ModClear là toà phúc thẩm mà nền tảng tập trung không bao
> giờ tự xây."

AI + web access là **trái tim**, không phải gia vị.

## 3. Cấu trúc thư mục

```
ModClear/
├── contracts/
│   ├── mod_clear.py         # Intelligent Contract chính (lõi sản phẩm)
│   └── storage_test.py      # contract sanity, deploy TRƯỚC để test môi trường
├── frontend/
│   ├── index.html           # dApp single-file gọi thật qua genlayer-js
│   └── src/config.js        # CONTRACT_ADDRESS + CHAIN, điền sau khi deploy
├── tests/test_mod_clear.py
├── scripts/deploy.sh
├── docs/{ARCHITECTURE.md, COMMON_ERRORS.md, samples/SCENARIOS.md}
├── CHANGELOG.md
└── README.md
```

## 4. Vòng đời (state machine) — đừng phá

```
file_appeal(payable) → FILED
FILED → adjudicate() [AI Jury] → REVIEWING → RESOLVED
RESOLVED → settle_fee() → CLOSED
```

Method ghi: `file_appeal`, `adjudicate`, `settle_fee`, `withdraw_treasury` (owner).
View: `get_appeal`, `get_total_appeals`, `get_treasury`.

Ruling: `UPHELD` (nền tảng đúng) / `OVERTURNED` (gỡ oan) / `PARTIAL` (một phần).
Phí: OVERTURNED/PARTIAL → hoàn creator; UPHELD → treasury.

## 5. Thiết kế đồng thuận — phần quan trọng NHẤT để giữ điểm

Trong `adjudicate()`:
- `leader_fn`: render `content_url` + `policy_url` → `exec_prompt(response_format="json")`
  trả `{ruling, confidence, rationale}`. Nguyên tắc xử: chỉ xét theo điều khoản
  được viện dẫn (hẹp); gánh nặng chứng minh thuộc bên thực thi; "khó chịu" ≠
  "vi phạm"; mơ hồ/không đọc được → nghiêng OVERTURNED.
- `validator_fn`: **KHÔNG chỉ kiểm schema**. Nó (1) validate ruling/confidence;
  (2) đọc lại nội dung + chính sách, chạy LLM riêng ra ruling độc lập; (3) TỪ
  CHỐI khi leader và validator ra hai cực đối nghịch (UPHELD vs OVERTURNED).
  PARTIAL tương thích với cả hai phía.

→ Khi mở rộng, TUYỆT ĐỐI không hạ validator xuống "chỉ kiểm JSON keys". Đó là
ranh giới giữa điểm 1 và điểm 4+.

## 6. RÀNG BUỘC KỸ THUẬT SỐNG CÒN (GenLayer) — tuân thủ tuyệt đối

1. Dòng đầu file contract phải là `# v0.2.16`, dòng 2 là `# { "Depends": "py-genlayer:..." }`.
2. KHÔNG gán `TreeMap()` / `DynArray()` trong `__init__` — GenVM tự khởi tạo rỗng.
3. KHÔNG dùng `float` trong chữ ký method public — dùng `int`.
4. Kiểu public hợp lệ: `str,bool,bytes,int`, sized ints (`u8..u256`,`i8..i256`),
   `Address`, `DynArray[T]`, `TreeMap[K,V]`. KHÔNG `list`/`dict`/generic chưa
   instantiate/custom class trong chữ ký public.
5. Storage dùng `TreeMap`/`DynArray`, KHÔNG `dict`/`list`.
6. Class chính tên đúng `Contract`, extends `gl.Contract`.
7. Mọi `gl.nondet.*` phải nằm trong `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`.
8. Chỉ `from genlayer import *`. KHÔNG `import genlayer as gl` / `import genlayer`.

Chi tiết + cách debug trong `docs/COMMON_ERRORS.md`.

## 7. Frontend

`frontend/index.html` dùng `genlayer-js` (CDN ESM): `writeContract` cho action,
`readContract` cho view, `waitForTransactionReceipt` với `status:"FINALIZED"`.
Có loading state khi chờ consensus, hiển thị ruling + confidence + rationale.
Sau deploy, điền `CONTRACT_ADDRESS` trong `frontend/src/config.js`.

## 8. Deploy nhanh

- Studio: reset storage → hard refresh → deploy `storage_test.py` trước → rồi
  `mod_clear.py` → copy address vào `config.js`.
- CLI: `bash scripts/deploy.sh testnet-asimov`.

## 9. Định hướng khi mở rộng (milestone)

Giữ đúng "GenLayer fit" + "contract quality":
- Appeal vòng 2 (bên thua stake kháng nghị lại).
- Reputation cho nền tảng theo tỷ lệ bị OVERTURNED (minh bạch hoá lạm quyền).
- Multi-source: cross-check policy theo thời điểm (Wayback Machine) để xử đúng
  phiên bản chính sách tại lúc bị xử lý.
- Tách multi-contract: Policy Registry / Treasury / Appeals.
- Mỗi milestone cần: git diff + before/after + CHANGELOG entry + metric cụ thể.

---

**Khi sửa code, luôn tự hỏi: "Việc này có làm validator chỉ còn kiểm hình dạng
thay vì ý nghĩa không? Có phá vỡ 8 ràng buộc GenLayer không? Có làm phần AI/web
trở thành tuỳ chọn thay vì trái tim không?" — nếu có, làm lại.**
