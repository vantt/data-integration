status: complete

# Báo cáo deploy phase 3 (p91, attempt 01)

Deploy hoàn tất và đã xác minh: production đang chạy đúng SHA 25b6be42da201964361b863e2dd5fac7b150a828. Không cần rollback.

## Timeline (ICT, 2026-10-14)
- 09:21 pre-check: HEAD 97d05451; chỉ `.claude/settings.json` bị sửa (tracked); 25b6be42 là hậu duệ của HEAD; instigator 26/26 running; serving view = 152; có 1 run đang chạy (realtime 65352235).
- 09:22 coordinator duyệt câu hỏi q-p91-a01-01 (điều kiện: chờ khoảng trống không có run).
- 09:22:43 phát hiện khoảng trống; `docker compose stop data_platform` xong 09:22:54.
- Rollback point /tmp/deploy-rollback-sha = 97d05451...; /tmp/deploy-branch-sha = 25b6be42....
- `git merge --ff-only 25b6be42...` thành công; `git log --oneline -1` = 25b6be42.
- 09:22:59 `docker compose start data_platform`; healthy lúc 09:23:29, GraphQL trả lời (Dagster 1.13.17).
- Log khởi động (grep Auto-Setup/rolling models/Error/Traceback): không có dòng nào.

## Kiểm tra
- 7a instigator: 26/26 running trước và sau, diff = 0 differences.
- 7b realtime sau restart: sapo_v2 4a2bf3d5 (09:24:11–09:24:58) SUCCESS, cb896f98 (09:27:17) SUCCESS; hug 73f51014 (09:25:01) SUCCESS, bd1fa36c (09:28:02) SUCCESS; hourly 7189d503 SUCCESS.
- Run đầu tiên 4a2bf3d5: `dbt parse` và `dbt build --select fqn:*` đều kết thúc; 0 step failure; cả 10 asset check `std_column_contract_*` (std_customer_addresses, _contacts, _notes, _tags, std_order_events, std_order_tags, std_teams, std_team_members, std_targets, std_marketing_spend) đều chạy; tôi đối chiếu được 10 dòng "passed", không có check nào fail hoặc WARN. Lưu ý: log Dagster không in dòng tổng kết "Done. PASS=… ERROR=…" của dbt nên con số ERROR=0 được suy ra từ việc không có step failure và run SUCCESS, không phải từ dòng tổng kết.
- 7c serving view: 152 trước, 152 sau.
- 7d log container 20 phút gần nhất, grep error/traceback: không có dòng nào.

## Ghi chú
- Không chạy rollback. Không commit gì. 10 view std_* mới nằm trong main_staging (nếu sau này rollback thì chúng vẫn còn, vô hại).
- Checkout prod chỉ thay đổi bởi ff-merge; các thư mục untracked và `.claude/settings.json` của user giữ nguyên.

## Follow-up
- Coordinator theo dõi nightly 03:00 (pipeline_batch_nightly_schedule): phải xanh, không asset check nào mới đỏ, serving view vẫn 152, row-count trong ngưỡng.

## Câu hỏi chưa giải quyết
- Không có.
