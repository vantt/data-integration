from dagster import asset, Output, MetadataValue
import sys
import os

# Add dlt dir to path
# orchestration/assets/sapo_assets.py -> ../../ingestion
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DLT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../ingestion"))

if DLT_DIR not in sys.path:
    sys.path.append(DLT_DIR)

try:
    import run_orders_batch
    import run_history_log
    import run_webhook_consumer
    import run_customers_batch
    import run_customers_batch
    import run_accounts_batch
    import gsheet_targets
except ImportError as e:
    raise ImportError(f"Could not import dlt scripts from {DLT_DIR}. Error: {e}")

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
                
                # Remove inline comments if present (careful with quotes)
                # Simple approach: split by # if not inside quotes. 
                # For env files, usually # starts a comment.
                
                if "#" in line:
                    # Very naive strip, assuming # is not part of the value unless quoted
                    # But .env usually expects straightforward KEY=VALUE
                    pass
                
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Handle inline comments for .env validation
                    # value="secret" # comment -> value="secret"
                    if " #" in value:
                        value = value.split(" #", 1)[0].strip()
                    
                    value = value.strip('"').strip("'")
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



@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_orders_batch_asset(context):
    """
    Daily batch sync for Sapo Orders.
    Captures 'modified_on' updates.
    """
    context.log.info("Starting Sapo Orders Batch Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        # Pass empty list to ignore sys.argv (Dagster args)
        load_info = run_orders_batch.run(argv=[])
    finally:
        os.chdir(cwd)
    context.log.info(f"Orders Batch Sync Finished. Info: {load_info}")
    return Output(
        value="Orders Batch Sync Completed", 
        metadata={
            "load_info": str(load_info)
        }
    )

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_customers_batch_asset(context):
    """
    Daily batch sync for Sapo Customers.
    """
    context.log.info("Starting Sapo Customers Batch Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_customers_batch.run(argv=[])
    finally:
        os.chdir(cwd)
    context.log.info(f"Customers Batch Sync Finished. Info: {load_info}")
    return Output(
        value="Customers Batch Sync Completed", 
        metadata={
            "load_info": str(load_info)
        }
    )

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_accounts_batch_asset(context):
    """
    Daily batch sync for Sapo Accounts (Staff).
    """
    context.log.info("Starting Sapo Accounts Batch Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_accounts_batch.run(argv=[])
    finally:
        os.chdir(cwd)
    context.log.info(f"Accounts Batch Sync Finished. Info: {load_info}")
    return Output(
        value="Accounts Batch Sync Completed", 
        metadata={
            "load_info": str(load_info)
        }
    )

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_history_log_asset(context):
    """
    Incremental poll of Sapo History Logs.
    Runs every 10 minutes to capture events.
    """
    context.log.info("Starting History Log Poll...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_history_log.run(argv=[])
    finally:
        os.chdir(cwd)
    context.log.info(f"History Log Finished. Info: {load_info}")
    return Output(
        value="History Log Completed",
        metadata={
            "load_info": str(load_info)
        }
    )

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_webhook_consumer_asset(context):
    """
    High-frequency poll of Cloudflare D1 Webhooks.
    Runs every minute.
    """
    context.log.info("Starting Webhook Consumer One-Off Run...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        # Use --once flag
        load_info = run_webhook_consumer.run(argv=['--once'])
    finally:
        os.chdir(cwd)
    context.log.info(f"Webhook Poll Finished. Info: {load_info}")
    return Output(
        value="Webhook Poll Completed",
        metadata={
            "load_info": str(load_info) if load_info else "No Data"
        }
    )

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_targets_asset(context):
    """
    Manual/Scheduled sync for Google Sheet Targets.
    """
    context.log.info("Starting Google Sheet Targets Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        gsheet_targets.run()
        load_info = "Success"
    except Exception as e:
        context.log.error(f"Error: {e}")
        raise e
    finally:
        os.chdir(cwd)
    
    context.log.info(f"Targets Sync Finished.")
    return Output(
        value="Targets Sync Completed", 
        metadata={
            "status": "Success"
        }
    )
