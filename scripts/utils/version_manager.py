import os
import argparse
import glob
import re
import shutil
import datetime
import sys

# Constants
DEFAULT_KEEP_VERSIONS = 5
VERSION_PREFIX = "v_"
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

def get_timestamp_str():
    """Generates a timestamp string for versioning."""
    return datetime.datetime.now().strftime(TIMESTAMP_FORMAT)

def get_new_version_path(base_dir):
    """
    Creates a new version directory path.
    Args:
        base_dir (str): Base directory for exports (e.g., .../data_lake/export/marts)
    Returns:
        str: Absolute path to the newly created version directory.
    """
    timestamp = get_timestamp_str()
    version_name = f"{VERSION_PREFIX}{timestamp}"
    full_path = os.path.join(base_dir, version_name)
    
    # Ensure base_dir exists
    os.makedirs(base_dir, exist_ok=True)
    
    # Create the specific version directory
    os.makedirs(full_path, exist_ok=True)
    
    return full_path

def cleanup_old_versions(base_dir, keep=DEFAULT_KEEP_VERSIONS):
    """
    Removes old version directories, keeping the latest N.
    Args:
        base_dir (str): Base directory containing version folders.
        keep (int): Number of recent versions to keep.
    """
    if not os.path.exists(base_dir):
        print(f"Base directory {base_dir} does not exist. Skipping cleanup.")
        return

    # Find all directories matching v_YYYYMMDD_HHMMSS
    # We rely on string sorting since YYYYMMDD_HHMMSS is strictly increasing
    subdirs = [
        os.path.join(base_dir, d) 
        for d in os.listdir(base_dir) 
        if os.path.isdir(os.path.join(base_dir, d)) and d.startswith(VERSION_PREFIX)
    ]
    
    # Sort descending (newest first)
    subdirs.sort(reverse=True)
    
    if len(subdirs) <= keep:
        print(f"Found {len(subdirs)} versions (Limit: {keep}). No cleanup needed.", file=sys.stderr)
        return

    # Delete older versions
    versions_to_delete = subdirs[keep:]
    print(f"Cleanup: Found {len(subdirs)} versions. Deleting {len(versions_to_delete)} old versions...", file=sys.stderr)
    
    for path in versions_to_delete:
        try:
            print(f"  Deleting: {os.path.basename(path)}", file=sys.stderr)
            shutil.rmtree(path)
        except Exception as e:
            print(f"  Error deleting {path}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Manage Data Layer Versions (Create & Cleanup)")
    parser.add_argument("--action", choices=["create", "cleanup", "create_and_cleanup"], required=True, help="Action to perform")
    parser.add_argument("--base-dir", required=True, help="Base directory for exports")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP_VERSIONS, help="Number of versions to keep")
    
    args = parser.parse_args()
    
    base_dir = os.path.abspath(args.base_dir)
    
    if args.action == "cleanup":
        cleanup_old_versions(base_dir, keep=args.keep)
        
    elif args.action == "create":
        new_path = get_new_version_path(base_dir)
        # Return only the path to stdout so calling scripts can capture it
        print(new_path)
        
    elif args.action == "create_and_cleanup":
        # First cleanup old ones to free space (optional strategy, or cleanup after)
        # Check policy: usually cleanup BEFORE creating creates space, but cleanup AFTER ensures we don't lose history if create fails?
        # Let's clean up existing generic old ones first.
        cleanup_old_versions(base_dir, keep=args.keep)
        new_path = get_new_version_path(base_dir)
        print(new_path)

if __name__ == "__main__":
    main()
