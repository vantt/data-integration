"""MISA AMIS — Playwright automation for downloading Sổ chi tiết tài khoản Excel.

Downloads all sub-accounts for a given account prefix (e.g. '642' covers 6421* + 6422*)
for the previous month, then drops the file into the account-ledger input directory.

Flow:
  1. Load shared cookies (same session as sales-ledger downloader)
  2. Navigate to GLAccountLedger report page
  3. Handle session-conflict dialog if present
  4. Click 'Chọn tham số' → set period dates (1st–last day of previous month)
  5. Search account prefix → click '.row-check-all' checkbox ('Chọn tất cả tài khoản')
     — this selects ALL matching accounts including deeply nested sub-accounts
  6. Click 'Xem báo cáo'
  7. Export Excel → Đồng ý → Tải tệp → save file
  8. Rename So_chi_tiet_{account}_{YYYYMM}.xlsx, persist cookies
"""
import json
import time
import importlib.util
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── Shared utilities — imported from sales-ledger downloader ───────────────────
# Cookie loading, browser helpers, and period_date_range are identical.

def _import_sales_downloader():
    spec = importlib.util.spec_from_file_location(
        "misa_sales_web_downloader",
        Path(__file__).parent / "misa_sales_web_downloader.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_sales = _import_sales_downloader()

load_cookies     = _sales.load_cookies
save_cookies     = _sales.save_cookies
period_date_range = _sales.period_date_range
login_headed     = _sales.login_headed
_wait_stable             = _sales._wait_stable
_screenshot              = _sales._screenshot
_dismiss_popups          = _sales._dismiss_popups
_handle_session_conflict = _sales._handle_session_conflict
_click_text              = _sales._click_text
_click_download_queue_icon = _sales._click_download_queue_icon

# ── Constants ──────────────────────────────────────────────────────────────────

REPORT_URL = "https://actapp.misa.vn/app/RP/ReportList/RPDynamicViewer/GLAccountLedger"

# Default account prefix — "642" captures all 6421* and 6422* sub-accounts.
# Override via download_account_ledger(account=...) or Dagster asset config.
DEFAULT_ACCOUNT = "642"


# ── Form helpers ───────────────────────────────────────────────────────────────

def _set_dates_for_period(page, period: str) -> None:
    """Fill Từ ngày / Đến ngày with the previous-month date range."""
    start_d, end_d = period_date_range(period)
    start_str = start_d.strftime("%d/%m/%Y")
    end_str   = end_d.strftime("%d/%m/%Y")
    print(f"    setting date range: {start_str} → {end_str}")
    date_inputs = page.locator("input.input-date")
    count = date_inputs.count()
    if count < 2:
        print(f"    [warn] only {count} date inputs found")
        return
    for i, val in enumerate([start_str, end_str]):
        try:
            inp = date_inputs.nth(i)
            inp.click(timeout=3000)
            inp.press("Control+A")
            inp.fill(val, timeout=3000)
            inp.press("Tab")
            time.sleep(0.5)
            print(f"    set date[{i}] = {val}")
        except Exception as e:
            print(f"    [warn] date[{i}] failed: {e}")


def _select_account_prefix(page, account: str) -> None:
    """Search for account prefix and click 'Chọn tất cả tài khoản' (.row-check-all).

    Unlike the TH header checkbox (which only selects visible paginated rows),
    the .row-check-all checkbox selects ALL accounts matching the search —
    including deeply nested sub-accounts not visible in the current list view.
    """
    search_selector = "input[placeholder='Nhập từ khóa tìm kiếm']"
    print(f"    selecting account prefix: {account}")
    try:
        inp = page.locator(search_selector).first
        inp.click(timeout=5000)
        inp.press("Control+A")
        inp.fill(account, timeout=3000)
        time.sleep(1.5)  # wait for list to filter

        _screenshot(page, f"acct_{account}_filtered")

        # Click the 'Chọn tất cả tài khoản' checkbox inside .row-check-all —
        # this selects every account matching the search, not just the visible page.
        clicked = page.evaluate("""() => {
            const row = document.querySelector('.row-check-all');
            if (row) {
                const cb = row.querySelector('input[type="checkbox"]');
                if (cb) { cb.click(); return 'row-check-all:' + (cb.className || '').slice(0, 40); }
            }
            return null;
        }""")
        if clicked:
            print(f"      clicked 'Chọn tất cả tài khoản' ({clicked})")
        else:
            print(f"      [warn] .row-check-all checkbox not found — falling back to TH checkbox")
            # Fallback: TH header checkbox (selects visible rows only)
            page.evaluate("""() => {
                for (const th of document.querySelectorAll('th')) {
                    const cb = th.querySelector('input[type="checkbox"]');
                    if (cb && cb.offsetParent !== null) { cb.click(); return; }
                }
            }""")
        time.sleep(0.5)

    except Exception as e:
        print(f"    [warn] account selection failed for {account}: {e}")


def _trigger_excel_export(page) -> None:
    """Click list-button export icon → Đồng ý → Tải tệp. Identical to sales ledger."""
    _screenshot(page, "before_export_click")

    # list-button that contains the Excel export icon
    try:
        btn_locator = page.locator(".list-button").filter(
            has=page.locator("[class*='mi-export__excel']")
        ).first
        btn_locator.click(timeout=5000)
        print("    clicked export list-button")
    except Exception as e:
        print(f"    [warn] list-button click failed: {e}")
        try:
            page.locator(".flex-center.print-button.list-button").first.click(timeout=5000)
            print("    clicked export list-button (fallback)")
        except Exception as e2:
            print(f"    [warn] export button not found: {e2}")

    time.sleep(2)  # let Tùy chọn dialog animate in

    # Click Đồng ý (use .last to avoid hidden duplicates)
    try:
        page.locator("[class*='ms-button-primary']").filter(has_text="Đồng ý").last.click(
            timeout=8000
        )
        print("    confirmed export dialog (Đồng ý)")
    except Exception as e:
        print(f"    [warn] Đồng ý click failed: {e}")

    # Wait for file to be generated (~6s), then wait for 'Tải tệp' link
    time.sleep(6)
    try:
        page.get_by_text("Tải tệp", exact=True).wait_for(timeout=30000)
    except Exception:
        print("    popup may have closed, reopening via queue icon")
        _click_download_queue_icon(page)
        time.sleep(2)

    _screenshot(page, "before_tai_tep")

    # Click 'Tải tệp' download link — exact match avoids hitting popup title
    try:
        page.get_by_text("Tải tệp", exact=True).first.click(timeout=8000)
        print("    clicked 'Tải tệp' (exact)")
    except Exception as e:
        print(f"    [warn] exact 'Tải tệp' click failed: {e}")
        try:
            page.locator(".status-text.flex-row").first.click(timeout=5000)
            print("    clicked 'Tải tệp' (.status-text.flex-row)")
        except Exception as e2:
            print(f"    [warn] .status-text click: {e2}")


# ── Main download flow ─────────────────────────────────────────────────────────

def _run_download_flow(page, period: str, timeout_seconds: int,
                       downloaded: list, output_dir=None,
                       account: str = DEFAULT_ACCOUNT) -> None:
    """Execute the full UI flow inside an authenticated browser context."""
    print("  [misa-al] Navigating to account ledger page...")
    try:
        page.goto(REPORT_URL, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"  [misa-al] goto timeout (continuing): {e}")

    _wait_stable(page, 12000)
    print(f"  [misa-al] URL: {page.url}")

    if "verify" in page.url:
        _handle_session_conflict(page)
        _wait_stable(page, 10000)

    if "GLAccountLedger" not in page.url:
        print(f"  [misa-al] SPA redirected, navigating again...")
        try:
            page.goto(REPORT_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            pass
        _wait_stable(page, 12000)

    for _ in range(5):
        if _dismiss_popups(page) == 0:
            break
        time.sleep(0.8)

    # Step 1: Open parameter panel
    print("  [misa-al] Clicking 'Chọn tham số'...")
    if not _click_text(page, "Chọn tham số"):
        raise RuntimeError("Could not find 'Chọn tham số' button")
    time.sleep(2)
    _dismiss_popups(page)
    _screenshot(page, "param_panel")

    # Step 2: Set period (date inputs — same reliable approach as sales ledger)
    print(f"  [misa-al] Setting period: {period}...")
    _set_dates_for_period(page, period)
    time.sleep(0.5)

    # Step 3: Select all accounts under prefix via .row-check-all
    print(f"  [misa-al] Selecting all accounts under prefix '{account}'...")
    _select_account_prefix(page, account)
    _screenshot(page, "accounts_selected")

    # Step 4: View report
    print("  [misa-al] Clicking 'Xem báo cáo'...")
    if not _click_text(page, "Xem Báo Cáo"):
        if not _click_text(page, "Xem báo cáo"):
            raise RuntimeError("Could not find 'Xem báo cáo' button")
    _wait_stable(page, 15000)
    time.sleep(1)
    _dismiss_popups(page)
    _screenshot(page, "report_loaded")

    # Step 5: Export Excel + capture download
    print("  [misa-al] Triggering Excel export...")
    try:
        with page.expect_download(timeout=(timeout_seconds + 30) * 1000) as dl_info:
            _trigger_excel_export(page)
        dl = dl_info.value
        fname = dl.suggested_filename or f"So_chi_tiet_tai_khoan_{int(time.time())}.xlsx"
        if output_dir:
            dest = Path(output_dir) / fname
            dl.save_as(str(dest))
            downloaded.append(dest)
            print(f"  [misa-al] Download captured: {fname} → {dest}")
        return
    except Exception as e:
        print(f"  [misa-al] expect_download failed: {e}")

    # Fallback: wait for on_download event handler
    print(f"  [misa-al] Waiting up to {timeout_seconds}s for download event...")
    t_start = time.time()
    while time.time() - t_start < timeout_seconds:
        if downloaded:
            print(f"  [misa-al] Download captured after {int(time.time() - t_start)}s")
            return
        time.sleep(2)
    time.sleep(10)
    if downloaded:
        print("  [misa-al] Download captured in grace period")
        return
    _screenshot(page, "timeout")
    raise RuntimeError(f"Download not received within {timeout_seconds + 10}s")


# ── Public API ─────────────────────────────────────────────────────────────────

def download_account_ledger(
    output_dir: Path,
    cookie_dir: Path,
    username: str,
    password: str,
    headless: bool = True,
    period: str = "thang_truoc",
    timeout_seconds: int = 300,
    account: str = DEFAULT_ACCOUNT,
) -> Path:
    """Download account-ledger Excel and return the renamed output path.

    Args:
        account: Account prefix to search and select (e.g. '642' for all 6421*/6422*).
                 Uses .row-check-all to select ALL matching accounts including sub-accounts.

    Uses shared MISA cookies. Re-logs in headed mode if cookies are absent/expired.
    """
    cookie_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    cookies = load_cookies(cookie_dir)
    if cookies is None:
        cookies = login_headed(username, password, cookie_dir)
        if not cookies:
            raise RuntimeError("Login failed — no cookies obtained")

    downloaded: list = []

    def on_download(dl):
        fname = dl.suggested_filename or f"So_chi_tiet_tai_khoan_{int(time.time())}.xlsx"
        dest  = output_dir / fname
        dl.save_as(str(dest))
        downloaded.append(dest)
        print(f"  [misa-al] Downloaded: {fname} → {dest}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=300)
        context = browser.new_context(accept_downloads=True)
        context.add_cookies(cookies)
        page = context.new_page()
        page.on("download", on_download)
        context.on("page", lambda new_page: new_page.on("download", on_download))

        try:
            _run_download_flow(page, period, timeout_seconds, downloaded, output_dir, account)
        except Exception as e:
            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
            err_path = Path(tempfile.gettempdir()) / f"misa_al_error_{ts}.png"
            try:
                page.screenshot(path=str(err_path))
            except Exception:
                pass
            print(f"  [misa-al] Error screenshot: {err_path}")
            raise
        finally:
            save_cookies(cookie_dir, context.cookies())
            browser.close()

    if not downloaded:
        raise RuntimeError("No file downloaded — check MISA session or report flow.")

    # Rename: So_chi_tiet_{account}_{YYYYMM}.xlsx
    raw_path = downloaded[0]
    start_d, _ = period_date_range(period)
    yyyymm = start_d.strftime("%Y%m")
    final  = raw_path.parent / f"So_chi_tiet_{account}_{yyyymm}.xlsx"
    if final.exists():
        final.unlink()
    raw_path.rename(final)
    print(f"  [misa-al] Renamed → {final.name}")
    return final
