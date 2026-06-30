# MISA Sales Ledger Auto-Download

**Goal:** Automate download of `So_chi_tiet_ban_hang` Excel from MISA AMIS web, drop into existing `run-misa-sales-file-drop` pipeline.

**Status:** BLOCKED — MISA login requires OTP via phone (2FA). Resume when phone available.

---

## Architecture Decision (settled)

```
[MISA web] → playwright download .xlsx
           → drop to app_data/input_source/misa-sales-ledger/
           → existing Dagster sensor triggers run-misa-sales-file-drop
           → existing parser → misa_raw/sales_lines parquet
```

No new pipeline, no new parser. New code = **1 file**: `ingestion/run-misa-sales-download.py`

---

## Login Issue

MISA login flow:
- URL: `https://amisapp.misa.vn/login/`
- Fields: `input[name='username']`, `input[name='pass']`, `input[name='captcha']`
- **2FA via phone OTP** — cannot automate headlessly on first login
- **Strategy:** Run headed once → user completes 2FA manually → save cookies → subsequent runs reuse cookies (same as Sapo pattern)

Cookie TTL: unknown — need to discover after successful login. Likely 24h session.

---

## Resume Steps

### Phase 0 — Discovery (needs phone, ~30 min)

1. Charge phone / have phone ready for OTP
2. Run `misa_explore.py` (already written in scratchpad):
   ```
   python "C:\Users\Vantt\AppData\Local\Temp\claude\...\misa_explore.py"
   ```
3. Complete login manually in headed browser (fill OTP from phone)
4. Script auto-navigates to report page and enters manual-monitor phase
5. Manually complete the full download flow (steps 3–10 as listed)
6. Script captures: download URL, headers, request method, cookies
7. Examine `misa_download_capture.json` + screenshots

### Phase 1 — Implement `run-misa-sales-download.py`

Based on discovery findings, implement:

```python
# ingestion/run-misa-sales-download.py
# 1. SharedCookieManager for misa_amis (source='misa_amis')
# 2. Custom login strategy — handle 2FA prompt (headed first time)
# 3. Navigate to report URL
# 4. Click "Chon tham so"
# 5. Select period: "tuan truoc" (Mon–Sun previous week)
# 6. Check "Chon tat ca" for vat tu + khach hang
# 7. Click "Xem Bao Cao"
# 8. Click "Xuat Excel" -> "Xuat Excel (dang du lieu)"
# 9. Click "Dong y"
# 10. Handle download event -> save to misa-sales-ledger/ input dir
# 11. Cookie file: ingestion/.cookies/misa_amis_cookies.json
```

**Key unknowns to resolve in Phase 0:**
- [ ] Does 2FA repeat every session or only on new device? (likely new device only)
- [ ] What is the download mechanism: direct URL, blob download, or iframe?
- [ ] What is the cookie TTL after login?
- [ ] Does "tuan truoc" map to a dropdown value or date range picker?
- [ ] Are "Chon tat ca" checkboxes auto-selected by default?

### Phase 2 — Dagster integration

- Wire `run-misa-sales-download.py` as a Dagster asset (weekly schedule, Monday morning)
- Or: simple cron job calling the script → sensor picks up the file

---

## Files

| File | Status |
|------|--------|
| `ingestion/run-misa-sales-download.py` | TO CREATE |
| `ingestion/src/misa_amis/misa-sales-web-downloader.py` | TO CREATE (if complex enough to modularize) |
| `ingestion/.cookies/misa_amis_cookies.json` | auto-created on first run |
| Exploration script (scratchpad) | READY — waiting for phone |

## References

- Existing ingestion: `ingestion/run-misa-sales-file-drop.py`
- Cookie pattern: `ingestion/src/utils/shared_cookie_manager.py`
- Login strategy pattern: `ingestion/src/sapo/login.py`
- Input dir: `app_data/input_source/misa-sales-ledger/`
- Report URL: `https://actapp.misa.vn/app/SA/ReportAnalysis/RPDynamicViewer/SalesBookDetailDefault`
