# Quy trình TAY sinh approach-script (đơn giản nhất)

Dùng khi script còn **tạo tay** (chưa auto-gen). 3 bước. Vòng lặp lặp lại mỗi đợt.

## Bước 1 — PREP (sinh prompt)
```bash
python scripts/build_approach_prompts.py            # cohort mặc định (recency<=270)
# tùy chọn:
python scripts/build_approach_prompts.py --recency 365 --limit 50
python scripts/build_approach_prompts.py --ids 895489673,603264280   # chỉ vài khách
```
→ Ghi `approach_prompts/{customer_id}.txt` mỗi khách (template v2 + data khách ráp sẵn).
Tên file = **customer_id** → biết output GPT lưu thành `{customer_id}.json`.

## Bước 2 — GEN (tay, GPT)
Mở mỗi `approach_prompts/{customer_id}.txt` → **dán nguyên vào GPT** → lưu JSON output thành `approach_out/{customer_id}.json` (giữ đúng tên customer_id).

## Bước 3 — LOAD (nạp vào CRM)
```bash
python scripts/load_approach_scripts.py --src approach_out/
```
→ Copy vào `{data_dir}/approach_scripts/{customer_id}.json`.
CRM **tự nhận** (worklist badge "Có kịch bản" + cockpit tab "Gọi"), **KHÔNG restart** (phase 05 auto-handle).

> Trong Docker: data_dir = `/data` (volume `crm_data`). Loader chạy trong container:
> `docker compose exec crm python scripts/load_approach_scripts.py --src /path/in/container/`
> hoặc `docker cp approach_out/. crm:/data/approach_scripts/` rồi đổi tên `{customer_id}.json`.

## Kiểm tra
- `http://localhost:3007/worklist` → bật chip "Có kịch bản" → khách vừa nạp xuất hiện.
- Mở khách đó → tab "Gọi" → thấy talk-track.

---

## Đơn giản hơn nữa (tùy chọn — host-bind drop-in)
Nếu muốn **bỏ bước 3**: mount 1 thư mục host làm `approach_scripts` (docker-compose), rồi chỉ cần
thả `{customer_id}.json` vào đó là CRM đọc ngay. Cần sửa docker-compose 1 lần (host bind) + restart 1 lần.
Mặc định hiện tại dùng volume + loader (không cần đổi compose).

## Lưu ý
- Script ra `recommended=true` → cockpit hiện talk-track; nếu GPT trả `recommended=false` (khách nghi B2B) → cockpit tự hiện STOP (R14).
- `consent_contact` set sẵn `allowed` (chính sách mặc định liên hệ được).
- Cohort gating khớp `retail-ai-outreach-cohort.sql`.
