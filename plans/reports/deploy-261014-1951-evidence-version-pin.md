# Deploy 14/10/2026 19:55: ghim version Evidence

## Kết quả

`main` được fast-forward từ `111f1386` lên `c2915881` (nhánh `chore/pin-evidence-versions`).
Chỉ đổi file trong repo: không rebuild, không restart container nào. `data_platform` và
`evidence` vẫn healthy sau merge.

| Commit | Nội dung |
|---|---|
| `fc7c98c9` | Ghim 5 package Evidence theo version đang chạy, thêm `package-lock.json` (lấy từ container đang chạy, 919/919 package khớp), `npm ci`, `evidence/README.md` |
| `c2915881` | Ghim image gốc `node:20.20.2-slim` (khớp image đang chạy: node 20.20.2, npm 10.8.2, Debian 12.13) |

Version ghim: `@evidence-dev/evidence` 40.1.8, `@evidence-dev/core-components` 5.4.2,
`@evidence-dev/duckdb` 2.0.1, `tailwindcss` 3.4.18, `autoprefixer` 10.5.4.

Các file đổi (`Dockerfile.evidence`, `evidence/package.json`, `evidence/package-lock.json`,
`evidence/README.md`) không được container nào mount, nên container đang chạy không đổi hành vi.

## Kiểm chứng trước merge (build cách ly)

Image `evidence-pin-test` build từ nhánh, chạy container riêng không mở cổng, không vào
`caddy_net`, lake mount chỉ đọc, `pages/`, `sources/`, `scripts/` là bản chép. Chạy hai lần
(sau mỗi commit), cả hai lần:

- `npm ci` thành công, `npm ls` ra đúng 5 version ghim;
- `evidence sources` đọc 9/9 nguồn, `evidence build` báo "Build complete";
- `/`, `/ceo-weekly-pulse/`, `/finance-cashflow/` trả 200, kích thước bằng trang prod ±1 byte.

`evidence sources` cần mạng ra ngoài: với `--network none` nó treo ở bước xử lý nguồn.
Container, image thử và bản chép dữ liệu đã xoá.

## Việc còn lại (user quyết thời điểm)

Version ghim chỉ có hiệu lực ở lần build image kế tiếp. Chạy vào giờ thấp điểm:

```bash
docker compose build evidence && docker compose up -d evidence
```

Sau đó chờ container healthy (build trang mất 1–3 phút) và kiểm `/`, `/ceo-weekly-pulse/`,
`/finance-cashflow/` trả 200 và hiển thị số liệu. Nếu hỏng: `git revert c2915881 fc7c98c9`,
rồi build lại.

## Ảnh hưởng tới phase 6

Nhánh `refactor/modularize-suite` (`95e6d1d7`) đang dựa trên `111f1386`. Khi deploy phase 6,
cần rebase nhánh đó lên `c2915881` để `git merge --ff-only` chạy được. Hai bên không đụng
file chung, nên rebase không đổi kết quả gate.
