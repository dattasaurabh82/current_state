#!/usr/bin/env python3
"""
Backup script for syncing generated music files to Dropbox.
Uploads only new .wav files that don't exist in Dropbox.
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Dropbox target folder
DROPBOX_FOLDER = "/currentStateMusicFilesBKP"

# Local music folder size limit in MB (for cleanup step)
MUSIC_DIR_SIZE_LIMIT_MB = 100

# Resolve paths relative to script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
MUSIC_DIR = PROJECT_ROOT / "music_generated"


def load_token():
    """Load Dropbox access token from .env file."""
    load_dotenv(ENV_FILE)
    token = os.getenv("DROPBOX_ACCESS_TOKEN")
    if not token:
        raise RuntimeError(f"DROPBOX_ACCESS_TOKEN not found in {ENV_FILE}")
    return token


def list_dropbox_files(token):
    """List files in Dropbox folder, return set of filenames."""
    url = "https://api.dropboxapi.com/2/files/list_folder"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = {"path": DROPBOX_FOLDER}

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 409:
        # Folder doesn't exist yet — treat as empty
        print(f"Dropbox folder '{DROPBOX_FOLDER}' not found, will create on first upload.")
        return set()

    response.raise_for_status()
    entries = response.json().get("entries", [])
    return {entry["name"] for entry in entries if entry[".tag"] == "file"}


def list_local_files():
    """List .wav files in local music_generated folder, return set of filenames."""
    if not MUSIC_DIR.exists():
        raise RuntimeError(f"Music directory not found: {MUSIC_DIR}")
    return {f.name for f in MUSIC_DIR.glob("*.wav")}


def upload_file(token, filepath):
    """Upload a single file to Dropbox."""
    url = "https://content.dropboxapi.com/2/files/upload"
    dropbox_path = f"{DROPBOX_FOLDER}/{filepath.name}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Dropbox-API-Arg": f'{{"path":"{dropbox_path}","mode":"add"}}',
        "Content-Type": "application/octet-stream",
    }

    with open(filepath, "rb") as f:
        response = requests.post(url, headers=headers, data=f)

    response.raise_for_status()
    return response.json()


def main():
    print("=== Dropbox Music Backup ===\n")

    # Load token
    token = load_token()
    print(f"Loaded token from: {ENV_FILE}")

    # List Dropbox files
    print(f"\nListing Dropbox folder: {DROPBOX_FOLDER}")
    dropbox_files = list_dropbox_files(token)
    print(f"  Found {len(dropbox_files)} file(s) in Dropbox:")
    for f in sorted(dropbox_files):
        print(f"    - {f}")

    # List local files
    print(f"\nListing local folder: {MUSIC_DIR}")
    local_files = list_local_files()
    print(f"  Found {len(local_files)} .wav file(s) locally:")
    for f in sorted(local_files):
        print(f"    - {f}")

    # Determine files to upload
    to_upload = local_files - dropbox_files
    print(f"\nFiles to upload: {len(to_upload)}")

    if not to_upload:
        print("Nothing to upload. All files already backed up.")
        return

    # Upload each file
    for i, filename in enumerate(sorted(to_upload), 1):
        filepath = MUSIC_DIR / filename
        print(f"\n[{i}/{len(to_upload)}] Uploading: {filename}")
        try:
            result = upload_file(token, filepath)
            print(f"  Done. Size: {result['size']} bytes")
        except requests.HTTPError as e:
            print(f"  FAILED: {e}")

    print("\n=== Backup Complete ===")

    # Cleanup check
    print("\n=== Cleanup Check ===")
    total_bytes = sum(f.stat().st_size for f in MUSIC_DIR.glob("*.wav"))
    total_mb = total_bytes / (1024 * 1024)
    print(f"Folder size: {total_mb:.1f} MB (limit: {MUSIC_DIR_SIZE_LIMIT_MB} MB)")

    if total_mb > MUSIC_DIR_SIZE_LIMIT_MB:
        latest_file = max(MUSIC_DIR.glob("*.wav"), key=lambda f: f.stat().st_mtime)
        print(f"Folder size exceeds limit. Would delete all .wav files except: {latest_file.name}")
    else:
        print("Folder size within limit. No deletions needed.")


if __name__ == "__main__":
    main()
