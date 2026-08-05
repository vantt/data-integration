# Phase 2 — Transfer code (git + uncommitted changes)

**Mục tiêu**: code trên vantt-mactu khớp 100% working tree hiện tại trên Windows, KỂ CẢ uncommitted changes (đặc biệt fix `dagster_home` trong `docker-compose.yml` — bỏ sót = tái tạo bug outage 9 ngày).

**Rủi ro chính đã xác định**: `git clone` đơn thuần KHÔNG đủ — thiếu 18 file uncommitted (`docker-compose.yml`, `orchestration/definitions.py`, `.claude/settings.local.json`, 14 file `.skills/ui-spec/**`) + nhiều file untracked trong `.skills/ui-spec/tools/wireframe/` và `plans/`.

## Bước

1. Verify git state trước khi transfer (chốt lại đúng những gì sẽ transfer):
   ```bash
   git status --short   # xác nhận danh sách M/?? không đổi so với lúc lập plan
   git log -1 --format='%H %ci'
   ```
2. Clone THẲNG vào thư mục đích đã tạo rỗng ở phase 1 (KHÔNG tạo subfolder `app/` — `docker-compose.yml` phải nằm ngay tại root vì dùng path tương đối `./app_data/...`):
   ```bash
   ssh vantt-mactu "git clone https://github.com/vantt/data-integration ~/projects/fg-data-warhouse"
   ssh vantt-mactu "cd ~/projects/fg-data-warhouse && git log -1 --format='%H %ci'"
   ```
   → xác nhận HEAD khớp Windows.
3. Transfer working-tree diff (uncommitted + untracked) — dùng `git diff` cho tracked, `tar` riêng cho untracked (loại trừ `.git`, `node_modules`, build artifact):
   ```bash
   # Tracked, modified — áp trực tiếp qua ssh
   git diff > /tmp/wt-diff.patch
   scp /tmp/wt-diff.patch vantt-mactu:~/migrate-staging/
   ssh vantt-mactu "cd ~/projects/fg-data-warhouse && git apply ~/migrate-staging/wt-diff.patch"

   # Untracked files — liệt kê rõ ràng (KHÔNG mirror toàn bộ working tree vì sẽ dính app_data/, node_modules nếu có)
   git status --porcelain | grep '^??' | cut -c4- > /tmp/untracked-list.txt
   tar -cf - -T /tmp/untracked-list.txt | ssh vantt-mactu "tar -C ~/projects/fg-data-warhouse -xf -"
   ```
4. Verify sau khi áp:
   ```bash
   ssh vantt-mactu "cd ~/projects/fg-data-warhouse && git diff docker-compose.yml" # phải khớp local diff
   ssh vantt-mactu "cd ~/projects/fg-data-warhouse && git status --short | wc -l"  # khớp số dòng local
   ```
5. Verify riêng đoạn fix quan trọng nhất — `dagster_home` named volume — đã có mặt:
   ```bash
   ssh vantt-mactu "grep -A2 'dagster_home:' ~/projects/fg-data-warhouse/docker-compose.yml | head -5"
   ```

## Rollback
Xoá `~/projects/fg-data-warhouse`, clone lại — không ảnh hưởng gì khác (chưa `docker compose up`).

## Acceptance
- HEAD commit khớp Windows.
- `git status --short` trên vantt-mactu liệt kê ĐÚNG cùng bộ file M/?? như Windows (không thiếu, không thừa).
- `docker-compose.yml` trên vantt-mactu có named volume `dagster_home` (không phải bind-mount `./app_data/dagster_home`).
