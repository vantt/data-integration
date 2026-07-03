"""
MISA AMIS — Playwright automation for downloading So chi tiet ban hang Excel.

Flow:
  1. Load saved cookies (or perform headed login on first run)
  2. Navigate to sales-ledger report page
  3. Handle session-conflict dialog ("Tiep tuc dang nhap")
  4. Dismiss first-time guideline popups ("Da hieu")
  5. Click "Chon tham so" → select period → check all vat tu & khach hang
  6. Click "Xem Bao Cao" → "Xuat Excel (dang du lieu)" → "Dong y" → "Tai Tep"
  7. Capture Playwright download event → save to output dir
  8. Persist updated cookies for next run
"""
import json
import time
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

from datetime import date

LOGIN_URL  = "https://amisapp.misa.vn/login/"
REPORT_URL = "https://actapp.misa.vn/app/SA/ReportAnalysis/RPDynamicViewer/SalesBookDetailDefault"


def period_date_range(period: str) -> tuple[date, date]:
    """Return (start, end) dates for the given period preset relative to today."""
    today = date.today()
    weekday = today.weekday()  # Mon=0, Sun=6
    if period == "tuan_truoc":
        # Previous Mon–Sun
        last_monday = today - timedelta(days=weekday + 7)
        return last_monday, last_monday + timedelta(days=6)
    if period == "tuan_nay":
        this_monday = today - timedelta(days=weekday)
        return this_monday, today
    if period == "thang_nay":
        start = today.replace(day=1)
        return start, today
    if period == "thang_truoc":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        start = last_prev.replace(day=1)
        return start, last_prev
    # Explicit month "YYYY-MM" → first..last calendar day of that month (for backfill)
    import re
    m = re.fullmatch(r"(\d{4})-(\d{2})", (period or "").strip())
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        start = date(y, mo, 1)
        end = (date(y, 12, 31) if mo == 12
               else date(y, mo + 1, 1) - timedelta(days=1))
        return start, end
    # Fallback: last 7 days
    return today - timedelta(days=7), today
COOKIE_TTL_HOURS = 168  # MISA x-sessionid lasts ~30 days; 7 days is conservative safe value


# ── Cookie persistence ─────────────────────────────────────────────────────────

def _cookie_path(cookie_dir: Path) -> Path:
    return cookie_dir / "misa_amis_cookies.json"


def load_cookies(cookie_dir: Path) -> Optional[list]:
    """Load Playwright-format cookies from file. Returns None if missing/expired."""
    path = _cookie_path(cookie_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Data is {"cookies": [...], "saved_at": "...", "ttl_hours": N}
        saved_at = datetime.fromisoformat(data["saved_at"])
        if saved_at.tzinfo is None:
            saved_at = saved_at.replace(tzinfo=timezone.utc)
        # Use max(saved TTL, current code TTL) so bumping COOKIE_TTL_HOURS takes effect immediately
        expires = saved_at + timedelta(hours=max(data.get("ttl_hours", COOKIE_TTL_HOURS), COOKIE_TTL_HOURS))
        if datetime.now(timezone.utc) > expires:
            print(f"  [misa] Cookies expired at {expires}")
            return None
        print(f"  [misa] Loaded {len(data['cookies'])} cookies (expire {expires.isoformat()})")
        return data["cookies"]
    except Exception as e:
        print(f"  [misa] Error loading cookies: {e}")
        return None


def save_cookies(cookie_dir: Path, cookies: list) -> None:
    """Save Playwright-format cookies with timestamp."""
    path = _cookie_path(cookie_dir)
    data = {
        "cookies": cookies,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "ttl_hours": COOKIE_TTL_HOURS,
    }
    # Atomic write
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(cookie_dir), suffix=".tmp")
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    Path(tmp_path).replace(path)
    print(f"  [misa] Cookies saved → {path}")


# ── Playwright helpers ─────────────────────────────────────────────────────────

def _wait_stable(page, timeout_ms: int = 10000) -> None:
    """Wait for networkidle with fallback to simple sleep."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except Exception:
        pass
    time.sleep(1)


_SCREENSHOT_DIR = Path(tempfile.gettempdir()) / "misa_debug"


def _screenshot(page, label: str) -> None:
    """Save a debug screenshot to temp dir (non-blocking on error)."""
    try:
        _SCREENSHOT_DIR.mkdir(exist_ok=True)
        ts   = datetime.now().strftime("%H%M%S")
        path = _SCREENSHOT_DIR / f"misa_{ts}_{label}.png"
        page.screenshot(path=str(path))
        print(f"  [misa] Screenshot: {path.name}")
    except Exception:
        pass


def _dismiss_popups(page) -> int:
    """Auto-click 'Da hieu' / 'Dong' / 'Bo qua' guideline popups. Returns count dismissed."""
    try:
        count = page.evaluate("""() => {
            let n = 0;
            for (const btn of document.querySelectorAll('button')) {
                const t = (btn.innerText || '').trim();
                if ((t === 'Đã hiểu' || t === 'Đóng' || t === 'Bỏ qua')
                        && btn.offsetParent !== null) {
                    btn.click(); n++;
                }
            }
            return n;
        }""")
        if count:
            print(f"  [misa] Dismissed {count} popup(s)")
        return count
    except Exception:
        return 0


def _handle_session_conflict(page) -> bool:
    """If MISA shows 'Tiep tuc dang nhap' conflict dialog, click it. Returns True if handled."""
    if "verify" not in page.url:
        return False
    try:
        clicked = page.evaluate("""() => {
            for (const btn of document.querySelectorAll('button')) {
                const t = (btn.innerText || '').trim();
                if (t.includes('Tiếp tục')) { btn.click(); return true; }
            }
            return false;
        }""")
        if clicked:
            print("  [misa] Clicked 'Tiep tuc dang nhap' (session conflict)")
            _wait_stable(page, 8000)
        return clicked
    except Exception:
        return False


def _click_text(page, text: str, timeout_ms: int = 10000) -> bool:
    """Click first visible element whose innerText matches text exactly or contains it."""
    try:
        page.locator(f"text={text}").first.click(timeout=timeout_ms)
        return True
    except Exception:
        pass
    # Fallback: JS click
    try:
        result = page.evaluate(f"""() => {{
            for (const el of document.querySelectorAll('button,[role=button],span,div,a')) {{
                const t = (el.innerText || el.textContent || '').trim();
                if (t === {json.dumps(text)} && el.offsetParent !== null) {{
                    el.click(); return true;
                }}
            }}
            return false;
        }}""")
        return result
    except Exception:
        return False


def _check_all_checkboxes_in_section(page, section_label: str) -> int:
    """Find checkbox 'Chon tat ca' near a section label and click it. Returns 1 if clicked."""
    # Try by aria label or nearby text
    try:
        result = page.evaluate(f"""() => {{
            const label = {json.dumps(section_label)};
            // Find any element containing the label text
            for (const el of document.querySelectorAll('*')) {{
                if ((el.innerText||'').trim().includes(label)) {{
                    // Look for nearby checkbox "Chon tat ca"
                    const parent = el.closest('.ms-list-title, .ms-combo, [class*=group], [class*=section]') || el.parentElement;
                    if (!parent) continue;
                    for (const chk of parent.querySelectorAll('input[type=checkbox],[role=checkbox]')) {{
                        if (chk.offsetParent !== null && !chk.checked) {{
                            chk.click(); return 1;
                        }}
                    }}
                }}
            }}
            return 0;
        }}""")
        return result
    except Exception:
        return 0


# ── Login (first-time, headed) ─────────────────────────────────────────────────

def login_headed(username: str, password: str, cookie_dir: Path) -> list:
    """
    Open visible browser for manual login. Blocks until user completes login.
    Saves and returns cookies.
    """
    from playwright.sync_api import sync_playwright

    print("[misa] No valid cookies found — opening browser for manual login.")
    print("       Please log in (username/password + OTP if required).")
    print("       Script will continue automatically after login is detected.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context()
        page = context.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)

        # Pre-fill credentials if possible
        try:
            page.fill("input[name='username']", username, timeout=3000)
            page.fill("input[name='pass']", password, timeout=3000)
        except Exception:
            pass

        # Wait up to 3 minutes for URL to leave login page
        deadline = time.time() + 180
        while time.time() < deadline:
            url = page.url
            if "login" not in url.lower() and "verify" not in url.lower():
                break
            # Handle verify/conflict pages
            if "verify" in url:
                _handle_session_conflict(page)
            remaining = int(deadline - time.time())
            if remaining % 15 == 0:
                print(f"  Waiting for login... {remaining}s remaining. URL={url}")
            time.sleep(3)

        cookies = context.cookies()
        browser.close()

    save_cookies(cookie_dir, cookies)
    return cookies


# ── Main download function ─────────────────────────────────────────────────────

def download_sales_ledger(
    output_dir: Path,
    cookie_dir: Path,
    username: str,
    password: str,
    headless: bool = True,
    period: str = "tuan_truoc",  # "tuan_truoc" | "thang_nay" | "thang_truoc"
    timeout_seconds: int = 300,
) -> Path:
    """
    Download So chi tiet ban hang Excel from MISA AMIS.

    Args:
        output_dir:  Where to save the downloaded .xlsx (= misa-sales-ledger input dir)
        cookie_dir:  Where to read/write misa_amis_cookies.json
        username:    MISA login email
        password:    MISA login password
        headless:    Run browser headlessly (False on first login attempt)
        period:      Report period preset to select
        timeout_seconds: Max seconds to wait for download

    Returns:
        Path to saved .xlsx file

    Raises:
        RuntimeError if download is not captured within timeout
    """
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    cookie_dir.mkdir(parents=True, exist_ok=True)

    # Load or obtain cookies
    cookies = load_cookies(cookie_dir)
    if not cookies:
        cookies = login_headed(username, password, cookie_dir)

    downloaded: list = []

    def on_download(dl):
        fname = dl.suggested_filename or f"So_chi_tiet_ban_hang_{int(time.time())}.xlsx"
        dest  = output_dir / fname
        dl.save_as(str(dest))
        downloaded.append(dest)
        print(f"  [misa] Downloaded: {fname} → {dest}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=300)
        context = browser.new_context(accept_downloads=True)
        context.add_cookies(cookies)
        page = context.new_page()
        # Attach download handler to ALL pages (main + any popup/new tab MISA opens)
        page.on("download", on_download)
        context.on("page", lambda new_page: new_page.on("download", on_download))

        try:
            _run_download_flow(page, period, timeout_seconds, downloaded, output_dir)
        except Exception as e:
            # Save error screenshot
            try:
                ts = datetime.now().strftime("%Y%m%dT%H%M%S")
                err_path = Path(tempfile.gettempdir()) / f"misa_error_{ts}.png"
                page.screenshot(path=str(err_path), full_page=True)
                print(f"  [misa] Error screenshot: {err_path}")
            except Exception:
                pass
            raise RuntimeError(f"MISA download flow failed: {e}") from e
        finally:
            # Always save updated cookies
            try:
                save_cookies(cookie_dir, context.cookies())
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass

    if not downloaded:
        raise RuntimeError("No file downloaded — check MISA session or report flow.")

    # Rename with period suffix: So_chi_tiet_ban_hang_YYYY-MM-DD_YYYY-MM-DD.xlsx
    raw_path = downloaded[0]
    start_d, end_d = period_date_range(period)
    suffix = f"_{start_d.strftime('%Y-%m-%d')}_{end_d.strftime('%Y-%m-%d')}"
    stem   = raw_path.stem.replace(" ", "_")
    final  = raw_path.parent / f"{stem}{suffix}{raw_path.suffix}"
    if final.exists():
        final.unlink()
    raw_path.rename(final)
    print(f"  [misa] Renamed → {final.name}")
    return final


def _run_download_flow(page, period: str, timeout_seconds: int, downloaded: list, output_dir=None) -> None:
    """Execute the full UI flow inside an already-authenticated browser context."""
    print(f"  [misa] Navigating to report page...")
    try:
        page.goto(REPORT_URL, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"  [misa] goto timeout (continuing): {e}")

    _wait_stable(page, 12000)
    print(f"  [misa] URL after first goto: {page.url}")

    # Handle session conflict (verify page)
    if "verify" in page.url:
        _handle_session_conflict(page)
        _wait_stable(page, 10000)

    # SPA may redirect to dashboard on first navigation — navigate again once SPA is bootstrapped
    if "ReportAnalysis" not in page.url:
        print(f"  [misa] SPA redirected to {page.url}, navigating to report again...")
        try:
            page.goto(REPORT_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"  [misa] second goto timeout (continuing): {e}")
        _wait_stable(page, 12000)
        print(f"  [misa] URL after second goto: {page.url}")

    # Dismiss guideline popups (may appear multiple times during flow)
    for _ in range(5):
        if _dismiss_popups(page) == 0:
            break
        time.sleep(0.8)

    # ── Step 3: Open parameter panel ────────────────────────────────────────
    print("  [misa] Clicking 'Chon tham so'...")
    if not _click_text(page, "Chọn tham số"):
        raise RuntimeError("Could not find 'Chon tham so' button")
    time.sleep(2)
    _dismiss_popups(page)
    _screenshot(page, "02_param_panel")

    # ── Step 4: Set report period via date inputs ────────────────────────────
    # MISA combo uses virtual scroll — options are not in DOM so combo selection
    # always fails. Date inputs are faster and fully reliable.
    print(f"  [misa] Setting period: {period}...")
    _set_dates_for_period(page, period)
    time.sleep(0.5)
    _screenshot(page, "03_period_selected")

    # ── Step 5: Check "Chon tat ca" vat tu ─────────────────────────────────
    print("  [misa] Selecting all vat tu + khach hang...")
    _select_all_items(page)
    time.sleep(1)

    # ── Step 6: Click "Xem Bao Cao" ─────────────────────────────────────────
    print("  [misa] Clicking 'Xem Bao Cao'...")
    if not _click_text(page, "Xem Báo Cáo"):
        if not _click_text(page, "Xem báo cáo"):
            raise RuntimeError("Could not find 'Xem Bao Cao' button")
    _wait_stable(page, 15000)
    time.sleep(1)
    _dismiss_popups(page)
    _screenshot(page, "04_report_loaded")

    # ── Step 7 & 8: Export Excel + capture download ──────────────────────────
    print("  [misa] Triggering Excel export...")
    try:
        with page.expect_download(timeout=(timeout_seconds + 30) * 1000) as dl_info:
            _trigger_excel_export(page)
        dl = dl_info.value
        fname = dl.suggested_filename or f"So_chi_tiet_ban_hang_{int(time.time())}.xlsx"
        if output_dir:
            dest = output_dir / fname
            dl.save_as(str(dest))
            downloaded.append(dest)
            print(f"  [misa] Download captured via expect_download: {fname} → {dest}")
        else:
            # Fallback: save to temp dir (on_download handler should have caught it)
            print(f"  [misa] Download captured via expect_download: {fname} (no output_dir)")
        return
    except Exception as e:
        print(f"  [misa] expect_download failed or timed out: {e}")

    # ── Step 9: Wait for on_download event (fallback) ────────────────────────
    print(f"  [misa] Waiting up to {timeout_seconds}s for download event...")
    t_start  = time.time()
    deadline = t_start + timeout_seconds
    while time.time() < deadline:
        if downloaded:
            elapsed = int(time.time() - t_start)
            print(f"  [misa] Download captured after {elapsed}s")
            return
        time.sleep(2)
    time.sleep(10)
    if downloaded:
        print("  [misa] Download captured in grace period")
        return
    _screenshot(page, "99_timeout")
    raise RuntimeError(f"Download not received within {timeout_seconds + 10}s")


def _select_period(page, period: str) -> None:
    """Select the Ky bao cao period using MISA's ms-combo component.

    MISA combo structure (no native <select>):
      div.ms-combo.ms-combo-box.normal   ← period combo (class 'normal' is unique to this field)
        div.combo-main-content
          div.selected-options           ← chip rendered as "Tháng này ×" (includes × button)
          input.combo-input              ← clicking this opens the dropdown list
    """
    period_vi = {
        "tuan_truoc":  "Tuần trước",
        "tuan_nay":    "Tuần này",
        "thang_nay":   "Tháng này",
        "thang_truoc": "Tháng trước",
    }
    target = period_vi.get(period, "Tuần trước")

    # Step 1: remove the current period chip if one is selected.
    # Chip innerText is e.g. "Tháng này ×" — use includes(), not exact match.
    removed = page.evaluate("""() => {
        const container = document.querySelector('.ms-combo-box.normal .selected-options');
        if (!container) return null;
        const chips = container.querySelectorAll('*');
        for (const chip of chips) {
            if (chip.offsetParent !== null && (chip.innerText || '').trim()) {
                const txt = chip.innerText.trim();
                chip.click();
                return txt;
            }
        }
        return null;
    }""")
    if removed:
        print(f"    removed existing chip: {removed.strip()}")
        time.sleep(0.8)

    # Step 2: open the dropdown by clearing the combo-input value.
    # The selected period is stored as input.value (e.g. "Tháng này").
    # Deleting the value triggers Vue's @input handlers → shows the period option list.
    combo_input = page.locator(".ms-combo-box.normal .combo-input").first
    try:
        combo_input.click(timeout=5000)
        time.sleep(0.5)
        combo_input.press("Control+A")
        time.sleep(0.2)
        combo_input.press("Delete")
        time.sleep(2)   # wait for dropdown to fully render
        print("    opened period dropdown (input cleared)")
    except Exception as e:
        print(f"    [warn] could not open combo-input: {e}")
        _set_dates_for_period(page, period)
        return

    _screenshot(page, "03a_period_dropdown_open")

    # Step 3: find and click the target option.
    # The dropdown may use virtual scroll — use scrollIntoView() to ensure item is reachable.
    found = page.evaluate(f"""() => {{
        const target = {json.dumps(target)};
        for (const el of document.querySelectorAll('li,div,span,a,[role=option]')) {{
            const t = (el.innerText || '').trim();
            if (t === target || t.includes(target)) {{
                el.scrollIntoView({{block: 'nearest'}});
                el.click();
                return el.tagName + ':' + (el.className||'').slice(0, 40);
            }}
        }}
        return null;
    }}""")
    if found:
        print(f"    selected period '{target}' (JS: {found})")
        time.sleep(0.8)
        return

    # Playwright fallback with wait (in case JS ran before DOM was ready)
    for selector in [
        f"li:has-text('{target}')",
        f"[role=option]:has-text('{target}')",
        f"[class*='option']:has-text('{target}')",
    ]:
        try:
            page.wait_for_selector(selector, timeout=4000)
            page.locator(selector).first.click(timeout=4000)
            print(f"    selected period '{target}' (Playwright: {selector})")
            time.sleep(0.8)
            return
        except Exception:
            pass

    print(f"    [warn] could not select period '{target}' — falling back to date inputs")
    _set_dates_for_period(page, period)


def _set_dates_for_period(page, period: str) -> None:
    """Directly fill Từ ngày / Đến ngày inputs — fallback when combo selection fails."""
    start_d, end_d = period_date_range(period)
    start_str = start_d.strftime("%d/%m/%Y")
    end_str   = end_d.strftime("%d/%m/%Y")
    print(f"    setting date range: {start_str} → {end_str}")
    date_inputs = page.locator("input.input-date")
    count = date_inputs.count()
    if count < 2:
        print(f"    [warn] only {count} input-date elements found — cannot set dates")
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
            print(f"    [warn] date input {i} failed: {e}")


def _select_all_items(page) -> None:
    """Check 'Chon tat ca' for both vat tu and khach hang sections."""
    # Try clicking checkboxes labeled "Chon tat ca" / "(Tất cả)"
    result = page.evaluate("""() => {
        let n = 0;
        for (const el of document.querySelectorAll('*')) {
            const t = (el.innerText || el.textContent || '').trim();
            if ((t === 'Chọn tất cả' || t === '(Tất cả)' || t === 'Tất cả')
                    && el.offsetParent !== null) {
                const chk = el.querySelector('input[type=checkbox]')
                         || el.closest('label')?.querySelector('input[type=checkbox]')
                         || (el.tagName === 'INPUT' ? el : null);
                if (chk && !chk.checked) { chk.click(); n++; }
                else if (!chk) { el.click(); n++; }
            }
        }
        return n;
    }""")
    if result:
        print(f"    checked {result} 'Chon tat ca' item(s)")


def _trigger_excel_export(page) -> None:
    """Click Xuat Excel list-button → Dong y in Tuy chon dialog → click Tai tep download link."""
    # 1. Open the export options dialog.
    # DOM confirmed: icon(mi-export__excel) → has-tooltip → flex-center.print-button.list-button
    # Use Playwright's click() for real browser mouse events (JS .click() is synthetic).
    exported = False
    _screenshot(page, "04b_before_export_click")

    try:
        btn_locator = page.locator(".list-button").filter(
            has=page.locator("[class*='mi-export__excel']")
        ).first
        btn_locator.click(timeout=5000)
        print("    clicked export list-button")
        exported = True
    except Exception as e:
        print(f"    [warn] list-button click failed: {e}")
        # Fallback by class only (no has-filter)
        try:
            page.locator(".flex-center.print-button.list-button").first.click(timeout=5000)
            print("    clicked export list-button (fallback)")
            exported = True
        except Exception as e2:
            print(f"    [warn] export button not found: {e2}")

    if not exported:
        print("    [warn] Could not find export button — check screenshot 04b")

    time.sleep(2)  # let Tuy chon dialog animate in
    _screenshot(page, "04c_after_export_click")

    # 2. list-button click opens the "Tuy chon" dialog directly.
    time.sleep(2)  # let dialog animate in

    # 3. Confirm "Dong y".
    # MISA <button class="ms-button-primary ..."> — use .last (hidden earlier buttons exist in DOM)
    try:
        page.locator("[class*='ms-button-primary']").filter(has_text="Đồng ý").last.click(
            timeout=8000
        )
        print("    confirmed export dialog (Đồng ý)")
    except Exception as e:
        print(f"    [warn] Đồng ý click failed: {e}")

    # 4. Wait for export popup + "Tải tệp" download link (~6s for server to generate)
    time.sleep(6)

    # Wait for "Tải tệp" to appear if still processing
    try:
        page.get_by_text("Tải tệp", exact=True).wait_for(timeout=30000)
    except Exception:
        # Popup may have auto-closed; reopen via queue icon
        print("    popup may have closed, reopening via queue icon")
        _click_download_queue_icon(page)
        time.sleep(2)

    _screenshot(page, "05_before_tai_tep")

    # 5. Click "Tải tệp" download link.
    # KEY: use get_by_text(exact=True) — "text=Tải tệp" partial-matches the popup
    #      title "Tải tệp Excel, tệp in,..." and clicks the wrong element.
    #      Real Playwright click (not JS .click()) needed so Chrome allows window.open().
    try:
        page.get_by_text("Tải tệp", exact=True).first.click(timeout=8000)
        print("    clicked 'Tải tệp' (exact)")
    except Exception as e:
        print(f"    [warn] exact 'Tải tệp' click failed: {e}")
        # Fallback by confirmed class from DOM inspection
        try:
            page.locator(".status-text.flex-row").first.click(timeout=5000)
            print("    clicked 'Tải tệp' (.status-text.flex-row)")
        except Exception as e2:
            print(f"    [warn] .status-text click: {e2}")


def _click_download_queue_icon(page) -> None:
    """Click the MISA download queue icon (ms-download / icon-feature-download) in top toolbar.

    Confirmed DOM: DIV.ms-download wraps DIV.icon-feature-download.mi-download--processed
    """
    # Use Playwright click for real browser events (Vue event system responds correctly)
    for selector in [
        ".ms-download",
        "[class*='icon-feature-download']",
        "[class*='mi-download--processed']",
    ]:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0:
                loc.click(timeout=5000)
                print(f"    clicked download queue icon ({selector})")
                return
        except Exception:
            pass

    # Last resort: JS click fallback
    result = page.evaluate("""() => {
        for (const el of document.querySelectorAll(
            '.ms-download,[class*="icon-feature-download"],[class*="mi-download"]')) {
            if (el.offsetParent !== null) { el.click(); return el.className.slice(0, 60); }
        }
        return null;
    }""")
    if result:
        print(f"    clicked download queue icon (JS: {result})")
    else:
        print("    [warn] Download queue icon not found — 'Tải tệp' may appear without opening queue")
