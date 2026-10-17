---
phase: 6
title: "Deployer Metabase an toàn I: sửa D1–D4 giữ tương thích 45 blueprint, harness Metabase tạm, test"
status: pending
priority: P1
effort: "2d"
dependencies: [4]
---

# Phase 06: Sửa các lỗi chặn của deployer, harness Metabase tạm

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: ghi hành vi nhận diện mới (tìm trong collection đích, trùng tên là lỗi, không tự dời) vào `.skills/metabase-automation/STRATEGY.md` §5.3. Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `.skills/metabase-automation/STRATEGY.md` (§5.3 danh tính, cờ mới, TLS); `.skills/metabase-automation/SKILL.md` (lệnh test, harness, biến môi trường); `.claude/commands/deploy-metabase-blueprint.md` (cờ mới, exit code); `docs/architecture/modules.md` (mục Analytics: deployer).

## Mục tiêu

Sửa bốn lỗi khiến deployer hiện tại có thể ghi đè dashboard prod (thiết kế §4 ⑦ mục 1), không làm gãy việc deploy 45 blueprint đang có, và dựng harness Metabase tạm để mọi phase sau test được mà không chạm prod. Bắt đầu sau phase 04, chạy trong 4 tuần lịch của phase 05 (khác file).

## Lỗi đã kiểm trong code

| # | Vị trí | Hành vi hiện tại | Sửa |
|---|---|---|---|
| D1 | `.skills/metabase-automation/lib/resources/Dashboard.js:8-11` (`find`), `:13-38` (`ensure`) | `GET /api/dashboard` toàn instance, khớp tên, rồi `PUT collection_id` dời dashboard sang collection đích và ghi đè | Tìm chỉ trong collection đích (`GET /api/collection/:id/items?models=dashboard`). Tìm thấy cùng tên ở collection khác: **dừng với lỗi**, không dời; chỉ dời khi có cờ `--allow-move <dashboard_id>` chỉ đích danh |
| D2 | `lib/resources/Card.js:29-35` (`findActiveInCollection`), gọi ở `scripts/deploy_from_markdown.js:430` | Card chưa nằm trên dashboard thì lấy card **cùng tên đầu tiên** trong collection rồi PUT SQL mới | Nếu có **hơn một** card cùng tên trong collection: dừng với lỗi (không đoán). Một card duy nhất: giữ hành vi cũ cho blueprint (tương thích), in cảnh báo. Đường spec v2 (phase 07) không dùng tìm theo tên |
| D3 | `scripts/deploy_from_markdown.js:590` (`main().catch(console.error)`), catch trong `Dashboard.syncCards` (`Dashboard.js:105` trở đi) | Lỗi bị nuốt, in "Deployment Complete", exit 0 | Lỗi ghi lan lên; `process.exitCode = 1`; in danh sách bước đã ghi trước khi lỗi |
| D4 | `lib/metabase_core.js:8` | `rejectUnauthorized: false` cho mọi HTTPS | Mặc định kiểm TLS; chỉ tắt khi `METABASE_TLS_INSECURE=1` và in cảnh báo mỗi lần chạy |

Ngoài ra: bỏ mặc định `"Sapo"` (`deploy_from_markdown.js:256`) **chỉ ở đường mới**; đường blueprint giữ mặc định để không gãy lệnh đang dùng (ghi trong STRATEGY là legacy).

## Harness Metabase tạm

- `.skills/metabase-automation/scripts/test/temp-metabase.sh up|down`: build image từ `Dockerfile.metabase` dưới tag `metabase-test` (cùng 0.62.3 và driver DuckDB), chạy container `metabase-test` cổng cố định **3101**, app DB H2 trong container (không mount volume), kiểm cổng trước khi chạy, `down` dừng và xoá container. Không dùng mạng `caddy_net`.
- Khởi tạo: `GET /api/session/properties` lấy `setup-token` → `POST /api/setup` tạo admin → session token; thêm database DuckDB trỏ tới **fixture tổng hợp** `analytics/tests/fixtures/serving_fixture.duckdb` (vài nghìn dòng giả, cùng tên view và cột public Weekly Pulse cần; sinh bằng `analytics/tests/fixtures/build_fixture.py` từ khai báo cột, không chép dữ liệu thật).
- Test bằng `node --test` (Node có sẵn), không thêm framework, không cần `package.json`.

## Test

- Đơn vị (mock `core.request`): `Dashboard.ensure` không dời khi tìm thấy ở collection khác; `Card` trùng tên → lỗi; lỗi PUT → exit code 1; TLS mặc định bật.
- Trên Metabase tạm: deploy 2 blueprint có sẵn (`ceo_weekly_pulse.md` và một blueprint có bộ lọc dùng `field_id`, ví dụ `finance_cashflow.md`, với `field_id_map` trỏ tới fixture) **hai lần**: số object bằng nhau, id giữ nguyên lần hai; tạo cố ý một dashboard cùng tên ở collection khác → deploy dừng với lỗi, dashboard kia không đổi `updated_at`.

## Files

- Sửa: `.skills/metabase-automation/lib/resources/{Dashboard,Card}.js`, `.skills/metabase-automation/lib/metabase_core.js`, `.skills/metabase-automation/scripts/deploy_from_markdown.js`.
- Tạo: `.skills/metabase-automation/scripts/test/temp-metabase.sh`, `.skills/metabase-automation/scripts/test/*.test.js`, `analytics/tests/fixtures/build_fixture.py`.
- Sửa tài liệu ở đầu file.

## Verification

- `node --test .skills/metabase-automation/scripts/test/` xanh.
- Harness: hai lần deploy ra cùng id; trường hợp trùng tên dừng đúng; exit code ≠ 0 khi lỗi.
- Container `metabase-test` đã dừng và xoá sau test; `ss -ltnp | grep 3101` trống.
- Không lệnh nào trỏ tới Metabase prod trong phase này.

## Đổi số?

Không. Không ghi vào Metabase prod.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Người dùng skill đang deploy blueprint bị chặn bởi lỗi trùng tên mới | Thông báo lỗi chỉ rõ card/dashboard trùng và cách xử lý; đó chính là chỗ trước đây ghi đè sai |
| Image `metabase-test` build lâu | Build một lần, giữ tag; không đụng image `metabase` của prod |

## Rollback

Revert commit. Không có gì chạy trên prod.
