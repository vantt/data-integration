"""
Sapo Client Module
Handles configuration loading, authentication, and session management for Sapo.
"""
import os
import dlt
from typing import Dict, Any, Optional
try:
    from utils.shared_cookie_manager import get_cookie_manager
except ImportError:
    from src.utils.shared_cookie_manager import get_cookie_manager
try:
    from .login import sapo_login_strategy
except ImportError:
    from sapo.login import sapo_login_strategy

def get_sapo_client() -> Any:
    """
    Constructs and returns a configured requests Session (via SharedCookieManager) for Sapo.
    Reads configuration from dlt.secrets.
    """
    # Try to get config from dlt config (merges config.toml + secrets.toml + env)
    config = dlt.config.get("sources.sapo") or {}

    domain = config.get("domain") or os.environ.get("SOURCES__SAPO__DOMAIN")
    base_url = config.get("base_url")
    login_url = config.get("login_url")
    
    # Auto-construct URLs from domain
    if domain:
        if not base_url:
            base_url = f"https://{domain}/admin"
        if not login_url:
            login_url = f"https://{domain}/admin/orders" # Default to orders or just admin/login? Usually admin/login but user uses orders
            
    # Fallbacks
    if not base_url:
         base_url = "https://fwg.mysapogo.com/admin"
    if not login_url:
         login_url = f"{base_url}/orders"

    # Default selectors
    default_selectors = {
        'username': '#pos-login-form #username',
        'password': '#pos-login-form #password',
        'submit': '#pos-login-form button.btn-login'
    }
    
    # Merge with user config
    login_selectors = default_selectors.copy()
    if config.get('login_selectors'):
        login_selectors.update(config.get('login_selectors'))

    # Credentials Fallback
    username = config.get('username') or os.environ.get("SOURCES__SAPO__USERNAME")
    password = config.get('password') or os.environ.get("SOURCES__SAPO__PASSWORD")

    if not username:
        raise ValueError("Missing 'username' in secrets.toml or SOURCES__SAPO__USERNAME env var")
    if not password:
        raise ValueError("Missing 'password' in secrets.toml or SOURCES__SAPO__PASSWORD env var")

    # Initialize cookie manager
    cookie_manager = get_cookie_manager('sapo', {
        'login_url': login_url,
        'username': username,
        'password': password,
        'cookie_ttl_hours': 6,
        'headless': config.get("headless", True),
        'cookie_ttl_hours': 6,

        'login_selectors': login_selectors,
        'domain': domain
    }, login_strategy=sapo_login_strategy)
    
    # Return a helper object or just the manager+base_url to use?
    # Returning a wrapper might be cleaner.
    
    return SapoClient(cookie_manager, base_url, config)

class SapoClient:
    def __init__(self, cookie_manager, base_url, config):
        self.cookie_manager = cookie_manager
        self.base_url = base_url
        self.config = config
        self.request_delay = float(config.get("request_delay", 0.5))
    
    @property
    def session(self):
        return self.cookie_manager.get_session()
        
    def refresh_session(self, current_session):
        """Refreshes cookies and updates the provided session in-place."""
        print("🔄 Refreshing session...")
        self.cookie_manager.login_and_save_cookies()
        new_session = self.cookie_manager.get_session()
        current_session.cookies.clear()
        current_session.cookies.update(new_session.cookies)
        current_session.headers.update(new_session.headers)
        return current_session
