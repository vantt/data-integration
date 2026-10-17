# Swap của host đầy (~8,1/8,2 GB): cái gì chiếm (15/10/2026)

## Kết luận

Swap đầy chủ yếu vì **`/tmp` là tmpfs và đang chứa 11 GB file tạm**. tmpfs nằm trong RAM; khi RAM
chật, kernel đẩy phần tmpfs ít dùng ra swap. `Shmem` = 4,8 GB đang nằm trong RAM, phần còn lại
(~6 GB) của `/tmp` nằm trong swap. Các tiến trình chỉ chiếm ~1,85 GB swap. Dữ liệu tạm của dự án
này chỉ ~46 MB; phần lớn là file tạm của các session Claude ở dự án khác và cache build.

Hệ quả cho dự án: container `evidence` (giới hạn 2 GiB RAM + 2 GiB swap) cần ~3,5 GiB khi build
trang, nhưng swap host đã hết nên build có thể bị OOM khi restart. Đã xử lý bằng `mem_limit: 4g`
trên nhánh `chore/evidence-auth`.

## Bằng chứng (chỉ đọc)

- `/proc/meminfo`: SwapTotal 8 GiB, SwapFree ~0; Shmem 4,6 GiB; MemAvailable ~12,7 GiB
  (RAM còn trống, swap thì hết).
- `df -t tmpfs`: `/tmp` tmpfs 16 GB, đã dùng 11 GB (71 %). `/dev/shm`, `/run` gần như trống; không
  có SysV shared memory.
- Tổng `VmSwap` của mọi tiến trình: ~1,85 GB. Lớn nhất: Metabase (java) ~390 MB, Dagster webserver
  ~105 MB, mỗi session `claude --resume` ~50–105 MB, gnome-shell, dev server Vite/pnpm.
- Lớn nhất trong `/tmp` (đều của user `vantt`):

| Đường dẫn | Dung lượng | Ghi chú |
|---|---|---|
| `/tmp/claude-1000/-home-vantt-projects-mcp-skill-hub/` | 4,5 GB | scratchpad của các session dự án mcp-skill-hub (một session 3,6 GB) |
| `/tmp/tmp.xX4qAHNGpI` | 2,1 GB | thư mục `mktemp` từ 14/10 17:30, chứa `go`, `home` (có vẻ toolchain/cache Go) |
| `/tmp/claude-1000/-home-vantt-projects-workshop-ecosystem/` | 1,1 GB | scratchpad session dự án workshop-ecosystem |
| `/tmp/node-compile-cache` | 802 MB | cache biên dịch của Node, từ 09/10 |
| `/tmp/tmp.70V4lxNnvT` | 786 MB | `mktemp` từ 11/10 |
| `/tmp/go-build*` | ~500 MB | cache build Go |
| `/tmp/claude-1000/-home-vantt-app-fg-dataware-house/` | 46 MB | dự án này |

## Đề xuất (chưa làm gì; các thư mục này không thuộc dự án này)

1. **Dọn file tạm cũ của các session khác** khi các session đó không còn cần (user quyết, vì có thể
   đang dùng): scratchpad mcp-skill-hub 4,5 GB, workshop-ecosystem 1,1 GB, các `tmp.*` cũ, cache
   `go-build*` và `node-compile-cache` (tự tạo lại được). Ước tính giải phóng ~8–9 GB tmpfs, tức gần
   hết swap.
2. **Lâu dài:** đừng để file tạm lớn nằm trên tmpfs. Đặt `TMPDIR`/`GOCACHE`/`GOTMPDIR` cho các công
   cụ build lên đĩa (vd. `~/.cache`), hoặc giảm kích thước tmpfs `/tmp` (đang 16 GB = một nửa RAM).
3. Với dự án này: `evidence` lên `mem_limit: 4g` (nhánh `chore/evidence-auth`) để build không dựa
   vào swap.
