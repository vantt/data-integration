import os
import sys
import subprocess
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def find_dbt_executable():
    """
    Finds the dbt executable. 
    1. Checks if 'dbt' is in PATH.
    2. Checks relative path to dlt/venv/Scripts/dbt.exe (common in this project).
    """
    # 1. Try finding in current python environment's scripts (best if running from venv)
    # If we are running with venv python, sys.executable points to .../venv/Scripts/python.exe
    # So dbt should be in .../venv/Scripts/dbt.exe
    venv_scripts = os.path.dirname(sys.executable)
    dbt_in_venv = os.path.join(venv_scripts, "dbt.exe" if os.name == 'nt' else "dbt")
    
    if os.path.exists(dbt_in_venv):
        return dbt_in_venv
        
    # 2. Try relative path from this script
    # transformation/scripts/run_dbt.py -> ../../dlt/venv/Scripts/dbt.exe
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    relative_dbt = os.path.join(project_root, "dlt", "venv", "Scripts", "dbt.exe")
    
    if os.path.exists(relative_dbt):
        return relative_dbt

    # 3. Fallback to PATH
    import shutil
    dbt_path = shutil.which("dbt")
    if dbt_path:
        return dbt_path
        
    return None

def run_dbt():
    parser = argparse.ArgumentParser(description="Run DBT Pipeline")
    parser.add_argument("--select", nargs='+', help="Model selection (passed to dbt build --select)", default=["+tag:mart"])
    parser.add_argument("--full-refresh", action="store_true", help="Pass --full-refresh to dbt")
    parser.add_argument("--target", help="DBT target", default=None)
    
    args = parser.parse_args()

    # 1. Resolve Executable
    dbt_exe = find_dbt_executable()
    if not dbt_exe:
        print("Error: Could not find 'dbt' executable.")
        sys.exit(1)
        
    print(f"Using dbt executable: {dbt_exe}")
    
    # 2. Set Working Directory to transformation/
    # script is in transformation/scripts/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    transformation_dir = os.path.dirname(script_dir)
    print(f"Working directory: {transformation_dir}")
    
    # 3. Construct Command
    # Pre-create Rolling Directories (Crucial for COPY command)
    dbt_export_path = os.environ.get("DBT_EXPORT_PATH")
    if dbt_export_path:
        print(f"Ensuring export directories in: {dbt_export_path}")
        if not os.path.exists(dbt_export_path):
            os.makedirs(dbt_export_path)
            
        # Scan transformation/models/marts
        # We are in transformation/scripts, so models is ../models
        models_dir = os.path.join(transformation_dir, "models", "marts")
        if os.path.exists(models_dir):
            for root, dirs, files in os.walk(models_dir):
                for file in files:
                    if file.endswith(".sql"):
                        model_name = os.path.splitext(file)[0]
                        model_path = os.path.join(dbt_export_path, model_name)
                        os.makedirs(model_path, exist_ok=True)

    cmd = [dbt_exe, "build"]
    
    if args.select:
        # Handle cases where multiple args are passed or space-separated strings
        # Flatten the list of selects
        flat_selects = []
        for item in args.select:
            flat_selects.extend(item.split())
            
        cmd.append("--select")
        cmd.extend(flat_selects)
        
    if args.full_refresh:
        cmd.append("--full-refresh")
        
    if args.target:
        cmd.extend(["--target", args.target])

    # 4. Run
    # Pass environment variables relative to this process
    env = os.environ.copy()
    
    print(f"Running: {' '.join(cmd)}")
    try:
        # shell=True on Windows can help with some path issues, but direct execution is safer if we have full path
        # Using shell=False and full path to exe
        # Hard timeout — prevents indefinite hang if dbt gets stuck.
        # 1 hour is plenty for the largest current build.
        process = subprocess.run(cmd, cwd=transformation_dir, env=env, check=True, timeout=3600)
        print("DBT Build Completed Successfully.")
    except subprocess.CalledProcessError as e:
        print(f"DBT Build Failed (Exit Code: {e.returncode})")
        sys.exit(e.returncode)
    except subprocess.TimeoutExpired:
        print("DBT Build timed out after 3600s — killed.")
        sys.exit(124)
    except Exception as e:
        print(f"Error running dbt: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_dbt()
