# PKF — Project Knowledge Framework

Skill Claude Code biến thư mục `pkf/` trong project của bạn thành một **kho tri thức dự án tự
lớn dần**: càng làm việc nhiều, project càng "nhớ" nhiều. Mọi thứ là Markdown thuần + YAML
frontmatter theo chuẩn [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog)
— đọc được bằng mắt, diff được bằng git, không database, không lock-in.

## PKF gồm 3 lớp

| Lớp | Vai trò | Ví von |
|---|---|---|
| `pkf/issues/` | Hồ sơ công việc: mỗi issue là **hợp đồng + biên bản + báo cáo** giữa bạn và AI — request nguyên văn, trao đổi có đánh số, plan có DoD, nghiệm thu có bằng chứng | GitHub Issues, nhưng sống trong repo |
| `pkf/docs/` | Tri thức hiện tại của app, mức what/why (không lặp code), chia theo topic, trỏ `sources` vào file code thực hiện | Wiki nội bộ do AI bảo trì, bạn duyệt |
| `pkf/log.md` | Nhật ký thay đổi toàn bundle, mới nhất trước | Changelog |

Triết lý đầy đủ (11 nguyên tắc: honesty, append-only, gate theo rủi ro, PM-level…):
[PHILOSOPHY.md](PHILOSOPHY.md).

## Cài đặt

1. **Copy thư mục skill** vào project (skill này nằm sẵn ở `.claude/skills/pkf/` của repo nào
   dùng nó; muốn dùng cho mọi project thì copy vào `~/.claude/skills/pkf/`).
2. **Python 3** có sẵn trên máy (PyYAML — thứ duy nhất 2 script validate/vẽ graph cần —
   sẽ được `/pkf init` tự kiểm tra và cài; muốn cài tay trước: `pip install pyyaml`).
3. Mở Claude Code trong project, chạy:
   ```
   /pkf init
   ```
   Lệnh này kiểm tra + cài môi trường toolchain (PyYAML) rồi tạo khung `pkf/` (issues/, docs/,
   log.md, index.md). Project có sẵn code (brownfield)
   sẽ được seed một bản đồ tri thức PM-level từ README/docs sẵn có; project mới tinh thì để
   trống, tri thức tự tích qua issue.

## Cách dùng

### Vòng đời điển hình của một việc

```
/pkf issue "mô tả yêu cầu/bug"     → AI search trùng lặp, phỏng vấn bạn đến khi rõ,
                                     tạo issue + Plan (checklist) + DoD; việc quan trọng
                                     thì DỪNG chờ bạn duyệt plan
/pkf work [id]                     → AI nạp đủ ngữ cảnh, kiểm tra đủ điều kiện mới làm,
                                     tick từng mục plan, verify DoD từng dòng,
                                     viết Resolution kèm bằng chứng → bạn xác nhận → resolved
```

### Toàn bộ lệnh

```
/pkf                            # = /pkf status; pkf/ chưa tồn tại thì đề nghị init
/pkf init                       # tạo khung lần đầu (một lần duy nhất)
/pkf issue "<yêu cầu>"          # tạo hồ sơ việc mới (bug/feature/docs/chore/…)
/pkf research [id] "<chủ đề>"   # research web có giới hạn: gắn issue thì bồi cho issue,
                                # không gắn thì làm giàu thẳng docs/ (bạn duyệt trước khi ghi)
/pkf work [id]                  # thực thi issue; không truyền id → liệt kê cho bạn chọn
/pkf status                     # ai đang chờ ai: việc chờ bạn duyệt, việc sẵn sàng làm,
                                # chuỗi blocked, việc ỳ lâu
/pkf query "<câu hỏi>"          # hỏi đáp từ tri thức đã tích ("X hoạt động sao?")
/pkf update                     # lưu insight/quyết định vừa chốt trong hội thoại vào docs
/pkf validate                   # kiểm tra chuẩn OKF + link gãy + mồ côi
/pkf viz                        # vẽ đồ thị tri thức (viz.html + graph.mmd)
```

Gõ tiếng Việt tự nhiên cũng được — "pkf báo lỗi X", "pkf làm issue 2", "pkf đang chờ gì" đều
route đúng lệnh.

### Bên trong một issue có gì

```
issue-<id>-<type>-<slug>.md      # vd: issue-8-chore-rebuild-exe-latest-fixes.md
├─ frontmatter                   # type, id, status, tags, blocked_by/blocks (dependency)
├─ # Request                     # yêu cầu NGUYÊN VĂN của bạn, có ngày
├─ # Discussion                  # biên bản: ### #1 — 2026-07-05 09:15 — User/AI,
│                                # chốt gì bôi đậm **Chốt:**, chỉ append không sửa cũ
├─ # Plan                        # checklist việc + **DoD:** (tiêu chí xong + cách verify)
├─ # Worklog                     # báo cáo tiến độ (chỉ khi việc kéo dài nhiều phiên)
├─ # Resolution                  # nghiệm thu: giải thích lại bằng lời thường + bằng chứng
└─ # Related                     # mọi tài liệu liên quan + Blocked by:/Blocks:
```

### Vai trò của bạn (những chỗ hệ thống chờ bạn)

- **Duyệt plan + DoD** khi việc chạm mức quan trọng (đổi hành vi user thấy, tiền, dữ liệu,
  kiến trúc) — AI dừng và chờ, không tự làm.
- **Xác nhận nghiệm thu**: mỗi Resolution mở đầu bằng đoạn AI giải-thích-lại; bạn xác nhận
  hoặc sửa — lời sửa được ghi nguyên văn.
- **Duyệt compile research**: tài liệu web AI thu về nằm ở `research/raw/` (bất biến), chỉ
  thành `docs/` khi bạn gật.
- Issue resolved **không bao giờ bị xoá** — lịch sử là tài sản.

## Khắc phục nhanh

| Vấn đề | Xử lý |
|---|---|
| `validate.py` báo thiếu PyYAML | `pip install pyyaml` |
| Validate báo broken link / orphan | Chạy `/pkf validate` rồi để AI tự sửa — mọi lệnh ghi file đều kết thúc bằng validate |
| Muốn xem toàn cảnh tri thức | `/pkf viz` → mở `pkf/viz.html` trong browser |

## Cấu trúc skill (cho ai muốn tuỳ biến)

```
.claude/skills/pkf/
├─ SKILL.md              # entry point AI đọc khi /pkf được gọi
├─ PHILOSOPHY.md         # triết lý bản lời thường (bản PRD: references/philosophy.md)
├─ README.md             # file này
├─ references/
│  ├─ commands/          # flow chi tiết từng lệnh (init, issue, work, …)
│  └─ concepts/          # luật chung: issue-lifecycle, docs-topics, research
├─ assets/templates/     # skeleton copy-paste: issue, doc, index, log
└─ scripts/              # validate.py, visualize.py (Python thuần + PyYAML)
```

Muốn đổi hành vi skill: đọc `references/philosophy.md` trước — mọi thay đổi phải đối chiếu
với PRD đó, đừng để skill trôi khỏi luật của chính nó.
