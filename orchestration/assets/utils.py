import os
import sys

# Add dlt dir to path
# orchestration/assets/utils.py -> ../../ingestion
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DLT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../ingestion"))

if DLT_DIR not in sys.path:
    sys.path.append(DLT_DIR)

def load_dlt_configuration(log_func=print):
    """
    Manually load .env.local and secrets.toml into os.environ.
    Includes handling for inline comments and robust fallback parsing.
    """
    log_func(f"[Config Loader] Loading configuration from {DLT_DIR}")
    
    # 1. Load .env.local
    env_local = os.path.join(DLT_DIR, ".env.local")
    if os.path.exists(env_local):
        log_func(f"[Config Loader] Found .env.local at {env_local}")
        with open(env_local, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Strip inline comments: KEY=value # comment OR KEY=value#comment
                    # But preserve # inside quoted values: KEY="val#ue"
                    if value and value[0] in ('"', "'"):
                        # Quoted value — find closing quote, ignore # inside
                        quote_char = value[0]
                        end_idx = value.find(quote_char, 1)
                        if end_idx != -1:
                            value = value[1:end_idx]
                        else:
                            value = value[1:]  # unclosed quote, strip opening
                    else:
                        # Unquoted — strip at first # (with or without leading space)
                        comment_idx = value.find("#")
                        if comment_idx != -1:
                            value = value[:comment_idx].rstrip()

                    os.environ[key] = value
                    # log_func(f"  [ENV] Loaded {key}")

    # 2. Load secrets.toml
    secrets_path = os.path.join(DLT_DIR, ".dlt", "secrets.toml")
    if os.path.exists(secrets_path):
        log_func(f"[Config Loader] Found secrets.toml at {secrets_path}")
        data = None
        try:
            import tomllib
            with open(secrets_path, "rb") as f:
                data = tomllib.load(f)
        except ImportError:
            try:
                import tomli
                with open(secrets_path, "rb") as f:
                    data = tomli.load(f)
            except ImportError:
                 log_func("[Config Loader] Warning: Neither tomllib nor tomli found. Using manual fallback.")

        if data:
            def flatten_config(d, prefix=""):
                for k, v in d.items():
                    key_upper = k.upper()
                    new_prefix = f"{prefix}__{key_upper}" if prefix else key_upper
                    if isinstance(v, dict):
                        flatten_config(v, new_prefix)
                    else:
                        if new_prefix not in os.environ:
                            os.environ[new_prefix] = str(v)
                            # log_func(f"  [TOML] Loaded {new_prefix}")

            flatten_config(data)
        else:
            # Improved Fallback Manual Parsing
            current_section = ""
            with open(secrets_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): 
                        continue
                    
                    # Handle inline comments
                    if " #" in line:
                        line = line.split(" #", 1)[0].strip()
                    
                    if line.startswith("[") and line.endswith("]"):
                        # [sources.sapo] -> SOURCES__SAPO
                        raw_section = line[1:-1]
                        current_section = raw_section.replace(".", "__").upper()
                        continue
                        
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip().upper()
                        v = v.strip()
                        v = v.strip('"').strip("'")
                        
                        if current_section:
                            env_key = f"{current_section}__{k}"
                        else:
                            env_key = k
                            
                        if env_key not in os.environ:
                             os.environ[env_key] = v
                             # log_func(f"  [FALLBACK] Loaded {env_key}")

    # Debug: Check if critical Sapo config is loaded
    sapo_domain = os.environ.get("SOURCES__SAPO__DOMAIN")
    sapo_user = os.environ.get("SOURCES__SAPO__USERNAME")
    
    if sapo_domain:
        log_func(f"[Config Loader] Verified SOURCES__SAPO__DOMAIN: {sapo_domain}")
    else:
        log_func("[Config Loader] ❌ SOURCES__SAPO__DOMAIN is MISSING in os.environ!")
        
    if sapo_user:
         log_func(f"[Config Loader] Verified SOURCES__SAPO__USERNAME: Set")
    else:
         log_func("[Config Loader] ❌ SOURCES__SAPO__USERNAME is MISSING in os.environ!")
