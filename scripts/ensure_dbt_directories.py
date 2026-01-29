import os
import glob
import sys

def ensure_directories():
    print("-> [Auto-Setup] checking dbt output directories...")

    # 1. Get Configuration
    # We expect this script to run inside Docker, where these env vars are set.
    # Fallback to relative path if running locally for debugging.
    dbt_export_path = os.environ.get("DBT_EXPORT_PATH")
    project_dir = os.environ.get("DBT_PROJECT_DIR", "/app/transformation")

    if not dbt_export_path:
        print("   [WARN] DBT_EXPORT_PATH not set. Skipping directory creation.")
        return

    # 2. Scan for Models (Marts only, as they are external tables)
    # Pattern: models/marts/**/*.sql
    models_pattern = os.path.join(project_dir, "models", "marts", "**", "*.sql")
    model_files = glob.glob(models_pattern, recursive=True)
    print(f"   [DEBUG] Scanning: {models_pattern}")
    print(f"   [DEBUG] Found {len(model_files)} models.")

    count = 0
    for model_file in model_files:
        # Extract model name (filename without extension)
        filename = os.path.basename(model_file)
        model_name = os.path.splitext(filename)[0]

        # Construct expected output directory
        # Pattern: {DBT_EXPORT_PATH}/{model_name}
        target_dir = os.path.join(dbt_export_path, "rolling", model_name)

        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
                print(f"   [+] Created directory: {target_dir}")
                count += 1
            except OSError as e:
                print(f"   [!] Failed to create {target_dir}: {e}")

    if count > 0:
        print(f"-> [Auto-Setup] Created {count} missing directories.")
    else:
        print("-> [Auto-Setup] All directories present.")

if __name__ == "__main__":
    ensure_directories()
