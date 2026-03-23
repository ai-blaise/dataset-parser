"""
Upload output-datasets/ to HuggingFace Hub.

Uses the Python API instead of the hf CLI to avoid OOM on large files —
the CLI hashes the entire file into memory, but the Python API streams.

Usage:
    uv run python scripts/upload_to_hf.py

Requires: hf auth login (run beforehand)
"""

import os
import sys

from huggingface_hub import HfApi

REPO_ID = "BlaiseAI/blaise-sft-training-mix"
LOCAL_DIR = "output-datasets"


def main():
    api = HfApi()

    # Verify auth
    try:
        user = api.whoami()
        print(f"Authenticated as: {user['name']}")
    except Exception as e:
        print(f"Not authenticated. Run 'hf auth login' first.\n{e}")
        sys.exit(1)

    # Collect all files to upload
    files = sorted(os.listdir(LOCAL_DIR))
    files = [f for f in files if os.path.isfile(os.path.join(LOCAL_DIR, f))]

    print(f"\nRepo: {REPO_ID}")
    print(f"Files to upload ({len(files)}):")
    for f in files:
        size_gb = os.path.getsize(os.path.join(LOCAL_DIR, f)) / (1024**3)
        print(f"  {f} ({size_gb:.2f} GB)")
    print()

    # Upload each file individually to avoid OOM
    for i, filename in enumerate(files, 1):
        filepath = os.path.join(LOCAL_DIR, filename)
        size_gb = os.path.getsize(filepath) / (1024**3)
        print(f"[{i}/{len(files)}] Uploading {filename} ({size_gb:.2f} GB)...")

        try:
            api.upload_file(
                path_or_fileobj=filepath,
                path_in_repo=filename,
                repo_id=REPO_ID,
                repo_type="dataset",
                commit_message=f"Upload {filename}",
            )
            print(f"  Done.")
        except Exception as e:
            print(f"  FAILED: {e}")
            sys.exit(1)

    print(f"\nAll {len(files)} files uploaded to https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
