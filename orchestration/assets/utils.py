import os
import sys

from dotenv import load_dotenv

# Add dlt dir to path
# orchestration/assets/utils.py -> ../../ingestion
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
DLT_DIR = os.path.join(PROJECT_ROOT, "ingestion")

if DLT_DIR not in sys.path:
    sys.path.append(DLT_DIR)


def load_dlt_configuration(log_func=print):
    """Load env vars for dlt pipelines. Idempotent, safe for both envs.

    Docker:  env vars already injected via docker-compose env_file → no-op.
    Local:   loads .env.local (project root) into os.environ.

    secrets.toml and config.toml are read natively by dlt when assets
    chdir to DLT_DIR before running pipelines — no manual flatten needed.
    """
    env_local = os.path.join(PROJECT_ROOT, ".env.local")
    loaded = load_dotenv(env_local, override=False)
    if loaded:
        log_func(f"[Config] Loaded .env.local from {env_local}")
    else:
        log_func("[Config] No .env.local — using docker-injected env vars")
