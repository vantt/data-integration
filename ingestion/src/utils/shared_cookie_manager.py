"""
Shared Cookie Management System
Supports multi-source authentication with file-based cookie persistence
"""

import json
import time
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Callable, Any
import requests

# File locking support
if os.name == 'nt':
    import msvcrt

    def lock_file(f):
        # Lock 1 byte at the current file position.
        # NOTE: msvcrt.locking only locks 1 byte, not the full file region.
        # Concurrent processes can still read/write outside the locked byte on NTFS.
        # This is best-effort defense-in-depth; atomic rename in _write_cookie_file
        # is the primary concurrency guard.  Allow 10 retries before raising.
        for _ in range(10):
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                time.sleep(0.1)
        # Final attempt
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

    def unlock_file(f):
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
else:
    import fcntl
    
    def lock_file(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def unlock_file(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class SharedCookieManager:
    """
    Thread-safe and process-safe cookie manager with file persistence.

    Features:
    - Auto login when cookies are invalid or expired
    - File-based storage with atomic writes
    - File locking for concurrent access
    - Support for multiple source systems

    Example:
        manager = SharedCookieManager(
            source='sapo_v2',
            login_url='https://admin.sapo.vn/login',
            username='user@example.com',
            password='password123'
        )
        session = manager.get_session()
        response = session.get('https://api.sapo.vn/orders')
    """

    def __init__(
        self,
        source: str,
        login_url: str,
        username: str,
        password: str,
        cookie_dir: str = ".cookies",
        cookie_ttl_hours: int = 6,
        login_selectors: Optional[Dict[str, str]] = None,
        headless: bool = True,
        login_strategy: Optional[Callable[[Any, str, str, Dict[str, str]], None]] = None,
        domain: Optional[str] = None
    ):
        """
        Initialize cookie manager.

        Args:
            source: Source system identifier (e.g., 'sapo_v2', 'shopify')
            login_url: URL of the login page
            username: Login username/email
            password: Login password
            cookie_dir: Directory to store cookie files
            cookie_ttl_hours: Hours before cookies expire (default: 6)
            login_selectors: Custom CSS selectors for login form
            headless: Run browser in headless mode (default: True)
            login_strategy: Custom callable(page, username, password, selectors) to handle login interaction
            domain: Optional domain or identifier to distinguish cookies for same source (e.g. store1.myshopify.com)
        """
        self.source = source
        self.login_url = login_url
        self.username = username
        self.password = password
        self.cookie_ttl_hours = cookie_ttl_hours
        self.password = password
        self.cookie_ttl_hours = cookie_ttl_hours
        self.headless = headless
        self.login_strategy = login_strategy
        self.user_agent = None
        self.domain = domain

        # Default login selectors (can be overridden)
        self.login_selectors = login_selectors or {
            'username': 'input[name="username"], input[type="email"], input[name="email"]',
            'password': 'input[name="password"], input[type="password"]',
            'submit': 'button[type="submit"], input[type="submit"]'
        }

        # Cookie file path
        # Use absolute path relative to the PROJECT ROOT (ingestion folder)
        # This ensures all processes (dbt, dagster, ad-hoc scripts) share the same file location
        # regardless of where they are invoked from.
        if os.path.isabs(cookie_dir):
             self.cookie_dir = Path(cookie_dir)
        else:
             # Assume 'ingestion' is the project root we want to anchor to.
             # Get the directory of THIS file (src/utils/shared_cookie_manager.py)
             # Go up 2 levels to get to 'ingestion'
             current_file_dir = Path(__file__).resolve().parent
             # ingestion/src/utils -> ingestion/src -> ingestion
             project_root = current_file_dir.parent.parent
             self.cookie_dir = project_root / cookie_dir
        
        self.cookie_dir.mkdir(parents=True, exist_ok=True)
        # Restrict directory permissions on Linux/Docker (no-op on Windows)
        if os.name != 'nt':
            os.chmod(self.cookie_dir, 0o700)
        
        # Construct filename with domain if present
        if domain:
            # Sanitize domain for filename
            safe_domain = "".join([c for c in domain if c.isalnum() or c in ('-', '_', '.')]).strip()
            filename = f"{source}_{safe_domain}_cookies.json"
        else:
            filename = f"{source}_cookies.json"
            
        self.cookie_file = self.cookie_dir / filename

        self.cookies = None
        self.cookie_expiry = None

    def _acquire_lock(self, file_handle, timeout: int = 10):
        """
        Acquire exclusive file lock with timeout.

        Args:
            file_handle: Open file handle
            timeout: Maximum seconds to wait for lock

        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        start_time = time.time()
        while True:
            try:
                lock_file(file_handle)
                return True
            except (IOError, OSError):
                if time.time() - start_time >= timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.cookie_file}")
                time.sleep(0.1)

    def _release_lock(self, file_handle):
        """Release file lock."""
        try:
            unlock_file(file_handle)
        except (IOError, OSError):
            pass

    def _read_cookie_file(self) -> Optional[Dict]:
        """
        Read cookies from file — no explicit lock.

        INVARIANT: this relies on _write_cookie_file using atomic rename
        (mkstemp + os.replace). DO NOT add an edit-in-place writer path —
        readers will observe partial JSON.

        Returns:
            Dictionary containing cookie data or None if file doesn't exist
        """
        if not self.cookie_file.exists():
            return None

        try:
            # Open with r+ to allow locking if needed, but r is enough for flock usually if we handled it well
            # But standard open in 'r' mode might not allow some locking operations on Windows
            # Let's stick to standard locking pattern.
            
            with open(self.cookie_file, 'r') as f:
                # We do not strictly need a write lock for reading, but to ensure consistency if someone is writing
                # For shared read lock, it's more complex on Windows with msvcrt.
                # Simplified: Just read. If we get partial read, json load handles error.
                # But to be safe against writing:
                # On Windows, we can't easily flock 'r' file.
                # Let's just try to read. The atomic write (rename) strategy below avoids partial reads.
                
                # Wait, the _write_cookie_file uses atomic rename. 
                # So we don't strictly need to lock for READ if we rely on atomic rename.
                # The file handle for reading will point to the old inode/file, while the writer creates a new one.
                # BUT if we want to ensure we don't read stale data while it's being updated (if not atomic)...
                # Atomic rename is the best way.
                
                # So for _read_cookie_file, we can just load.
                 data = json.load(f)
                 return data
                 
        except Exception as e:
            print(f"⚠️ [{self.source}] Error reading cookie file: {e}")
            return None

    def _write_cookie_file(self, data: Dict):
        """
        Write cookies to file with atomic operation and file locking.

        Uses a unique temp file (mkstemp) to prevent concurrent-write collision,
        then atomically replaces the target via os.replace (NTFS and POSIX safe).

        Args:
            data: Cookie data to write
        """
        try:
            # Unique temp file per write — eliminates concurrent-write collision
            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.cookie_dir), suffix='.tmp')
            temp_file = Path(tmp_path)

            with os.fdopen(tmp_fd, 'w') as f:
                try:
                    self._acquire_lock(f)
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    self._release_lock(f)

            # Atomic replace — os.replace is atomic on NTFS and POSIX; no pre-delete needed
            temp_file.replace(self.cookie_file)

            # Restrict file permissions on Linux/Docker (no-op on Windows)
            if os.name != 'nt':
                os.chmod(self.cookie_file, 0o600)

            print(f"💾 [{self.source}] Saved cookies to {self.cookie_file}")

        except Exception as e:
            print(f"⚠️ [{self.source}] Error writing cookie file: {e}")
            raise

    def load_cookies(self) -> bool:
        """
        Load cookies from file.

        Returns:
            True if valid cookies were loaded, False otherwise
        """
        data = self._read_cookie_file()

        if not data:
            return False

        try:
            self.cookies = data.get('cookies')
            expiry_str = data.get('expiry')

            if expiry_str:
                self.cookie_expiry = datetime.fromisoformat(expiry_str)

            if self.is_cookie_valid():
                self.user_agent = data.get('user_agent')
                print(f"✅ [{self.source}] Loaded valid cookies (expire: {self.cookie_expiry})")
                return True
            else:
                print(f"⚠️ [{self.source}] Cookies expired at {self.cookie_expiry}")
                return False

        except Exception as e:
            print(f"⚠️ [{self.source}] Error parsing cookie data: {e}")
            return False

    def is_cookie_valid(self) -> bool:
        """
        Check if cookies are still valid.

        Returns:
            True if cookies exist and not expired
        """
        if not self.cookies or not self.cookie_expiry:
            return False
        return datetime.now() < self.cookie_expiry

    def login_and_save_cookies(self) -> Dict[str, str]:
        """
        Perform login and save cookies to file.

        Uses Playwright to automate browser login.

        Returns:
            Dictionary of cookies

        Raises:
            Exception: If login fails
        """
        print(f"🔑 [{self.source}] Logging in to get new cookies...")
        
        # Lazy import playwright
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()

            try:
                # Navigate to login page
                print(f"   → Navigating to {self.login_url}")
                try:
                    page.goto(self.login_url, wait_until='domcontentloaded', timeout=30000)
                except Exception as goto_ex:
                    print(f"   ⚠️ Navigation timeout (domcontentloaded). Proceeding anyway... {goto_ex}")
                    # If it timed out but page might be loaded enough, we proceed.
                    # We rely on selectors waiting in the next steps.

                if self.login_strategy:
                    # Use custom strategy
                    print(f"   → Using custom login strategy for {self.source}")
                    self.login_strategy(page, self.username, self.password, self.login_selectors)
                else:
                    # Default generic login flow
                    # Fill login form
                    print(f"   → Filling credentials for {self.username}")
                    # Wait for selector to be visible
                    page.wait_for_selector(self.login_selectors['username'])
                    page.fill(self.login_selectors['username'], self.username)
                    page.fill(self.login_selectors['password'], self.password)
    
                    # Submit form
                    print(f"   → Submitting login form")
                    
                    # Check if button is disabled (common Sapo issue)
                    submit_btn = page.locator(self.login_selectors['submit'])
                    if submit_btn.is_disabled():
                         print("   ⚠️ Submit button is disabled. Waiting/Retrying interaction...")
                         # Try focusing fields again to trigger validation??
                         page.click(self.login_selectors['username'])
                         page.click(self.login_selectors['password'])
                         time.sleep(1)
    
                    page.click(self.login_selectors['submit'])
                    page.wait_for_load_state('networkidle', timeout=30000)

                # Verify logic: check if we are redirected away from login or have session cookies
                # User provided generic info, so we stick to URL check or just trust cookies.
                # Ideally, wait for a specific element that verifies logged-in state.
                
                # Check if still on login page?
                # Sometimes URL doesn't change immediately or is SPA.
                # Better to wait for some element or just wait a bit.
                time.sleep(2) 
                
                if 'login' in page.url.lower() and not 'dashboard' in page.url.lower():
                     # This is a weak check, but okay for generic.
                     print(f"⚠️ Warning: Still on login-like URL: {page.url}. Continues if cookies found.")

                # Extract cookies
                raw_cookies = context.cookies()
                # We need to map list of dicts to a dict of name:value
                self.cookies = {}
                for c in raw_cookies:
                    self.cookies[c['name']] = c['value']

                self.user_agent = page.evaluate("navigator.userAgent")
                
                self.cookie_expiry = datetime.now() + timedelta(hours=self.cookie_ttl_hours)

                # Save to file
                cookie_data = {
                    'source': self.source,
                    'cookies': self.cookies,
                    'user_agent': self.user_agent,
                    'expiry': self.cookie_expiry.isoformat(),
                    'created_at': datetime.now().isoformat(),
                    'login_url': self.login_url,
                }

                self._write_cookie_file(cookie_data)

                print(f"✅ [{self.source}] Login successful! Cookies valid until {self.cookie_expiry}")

            except Exception as e:
                print(f"❌ [{self.source}] Login failed: {e}")
                try:
                    # Write to a logs/ subdir with timestamp to avoid same-second overwrite
                    # when multiple pipelines fail login concurrently.
                    logs_dir = os.path.join(tempfile.gettempdir(), "data_integration_logs")
                    os.makedirs(logs_dir, exist_ok=True)
                    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    error_shot = os.path.join(logs_dir, f"{self.source}_login_error_{ts}.png")
                    page.screenshot(path=error_shot, full_page=True)
                    print(f"📸 Screenshot saved to {error_shot}")
                except Exception as sc_e:
                    print(f"⚠️ Could not save screenshot: {sc_e}")
                raise
            finally:
                browser.close()

        return self.cookies

    def get_valid_cookies(self) -> Dict[str, str]:
        """
        Get valid cookies - load from file or login if needed.

        Concurrency guard: a file-based exclusive lock around the
        check-and-refresh cycle prevents concurrent Dagster workers from
        spawning parallel Playwright browser sessions when cookies expire.
        Atomic rename in _write_cookie_file is still the primary safety net;
        the lock here prevents the redundant double-login scenario.

        Note on Windows: msvcrt.locking is best-effort (locks 1 byte).
        The atomic rename remains the primary concurrency guard; the lock
        reduces (but cannot fully eliminate) the race window on Windows.
        """
        # Fast path: in-process cache still valid
        if self.is_cookie_valid():
            return self.cookies

        # Slow path: acquire process-level file lock before check-and-refresh
        lock_path = self.cookie_file.with_suffix('.lock')
        with open(lock_path, 'a') as lock_fh:
            try:
                self._acquire_lock(lock_fh, timeout=30)
                # Re-check after acquiring lock — another process may have
                # refreshed cookies while we were waiting
                self.load_cookies()
                if not self.is_cookie_valid():
                    self.login_and_save_cookies()
            finally:
                self._release_lock(lock_fh)

        return self.cookies

    def get_session(self) -> requests.Session:
        """
        Get requests session with valid cookies.
        """
        session = requests.Session()
        cookies = self.get_valid_cookies()
        
        # requests expects a dict or CookieJar
        # self.cookies is a Dict[str, str]
        
        session.cookies.update(cookies)
        
        # Set User-Agent if available
        if self.user_agent:
            session.headers.update({'User-Agent': self.user_agent})
        else:
            # Fallback
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
        return session

    def get_cookie_header(self) -> str:
        """
        Get cookies as header string.
        """
        cookies = self.get_valid_cookies()
        return '; '.join([f"{k}={v}" for k, v in cookies.items()])

    def clear_cookies(self):
        """
        Force clear cookies (will force re-login on next use).
        """
        if self.cookie_file.exists():
            try:
                self.cookie_file.unlink()
            except OSError as e:
                print(f"⚠️ Error deleting cookie file: {e}")
        self.cookies = None
        self.cookie_expiry = None
        print(f"🗑️ [{self.source}] Cleared cookies")


def get_cookie_manager(source: str, config: Dict, login_strategy: Optional[Callable] = None) -> SharedCookieManager:
    """
    Factory function to create cookie manager.
    """
    return SharedCookieManager(
        source=source,
        login_url=config['login_url'],
        username=config['username'],
        password=config['password'],
        cookie_dir=config.get('cookie_dir', '.cookies'),
        cookie_ttl_hours=config.get('cookie_ttl_hours', 6),
        login_selectors=config.get('login_selectors'),
        headless=config.get('headless', True),
        login_strategy=login_strategy,
        domain=config.get('domain')
    )
