# Phase 4: đóng gói, phiên bản, CI, image

**Effort:** 1.5d · **Phụ thuộc:** phase 3; Q1–Q4 của plan · **Đụng prod:** không · **Cần user duyệt:** có, duyệt phát hành bản đầu

## Bối cảnh

CRM (và MCP phân tích) phải ghim được đúng một phiên bản host, kiểm được tính toàn vẹn, và nâng phiên bản có kiểm (plan, mục "Cách CRM ghim phiên bản").

## Yêu cầu

1. **Semver** và `CHANGELOG.md` (mỗi bản ghi: thay đổi, phiên bản Monty/quickjs-rs/MCP SDK đi kèm, dải `x-agent-catalog-version` hỗ trợ, thay đổi giới hạn mặc định).
2. **Khoá phụ thuộc:** `uv.lock`; xuất `requirements.lock` có hash cho người cài bằng pip.
3. **CI** (GitHub Actions hoặc hệ CI đã chọn ở Q2), mỗi commit và PR: lint, type-check, unit, hợp đồng runner, bộ tấn công trong container có `--memory`, test trọn vòng với backend giả, đo token của định nghĩa tool. Hằng tuần: chạy lại với bản Monty mới nhất (không phát hành) để biết sớm thay đổi.
4. **Image:** `Dockerfile` của repo: base ghim digest, user không đặc quyền, không shell thừa; cài từ `requirements.lock`; `ENTRYPOINT` chạy MCP server. CI dựng image, quét lỗ hổng (công cụ quét có sẵn trong CI đã chọn), đẩy lên registry theo tag semver; ghi digest vào release.
5. **Phát hành:** tag `vX.Y.Z` → release có wheel, `requirements.lock`, digest image, changelog. Không xoá hay ghi đè tag.
6. **Mẫu triển khai** `deploy/compose.example.yml`: service host với `mem_limit`, `pids_limit`, `read_only: true`, `tmpfs`, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, biến môi trường, healthcheck. Đây là mẫu cho `crm_codemode` của CRM.
7. Phát hành bản đầu (`v0.1.0` theo đề xuất Q4) sau khi user duyệt.

## File

Trong repo mới: `Dockerfile`, `.github/workflows/{ci,release,weekly}.yml` (hoặc tương đương), `deploy/compose.example.yml`, `CHANGELOG.md`, `requirements.lock`.

## Các bước

1. Khoá phụ thuộc, CI.
2. Dockerfile, quét, đẩy image thử lên registry.
3. Mẫu compose; chạy mẫu với backend giả trên máy dev.
4. Trình user, phát hành bản đầu.

## Test

| Mức | Nội dung |
|---|---|
| CI | Mọi job xanh trên nhánh chính; job tấn công chạy trong container giới hạn RAM |
| Image | Chạy với `read_only`, `cap_drop ALL`, user không đặc quyền: healthcheck xanh, 25 tác vụ mẫu chạy |
| Phát hành | Cài từ wheel + `requirements.lock --require-hashes` thành công trên máy sạch |

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Máy prod không kéo được image từ registry riêng | Trung bình × Thấp | Phương án wheel kèm hash, dựng image tại chỗ |
| Phụ thuộc bắc cầu thay đổi | Thấp × Trung bình | Khoá có hash; image ghim digest |

## Rollback

Bản lỗi: phát hành bản vá; bên dùng trả digest về bản trước.
