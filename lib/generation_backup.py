"""
Generation Results Backup Module

Uploads generation_results/ as a dated zip to Dropbox.
Modular and optional - controlled via settings.json.

Usage:
    from lib.generation_backup import backup_generation_results
    backup_generation_results()  # Call after pipeline completes
"""

import json
import os
import zipfile
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from loguru import logger

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
SETTINGS_FILE = PROJECT_ROOT / "settings.json"
GENERATION_RESULTS_DIR = PROJECT_ROOT / "generation_results"

# Dropbox target folder (same as music backup)
DROPBOX_FOLDER = "/currentStateMusicFilesBKP"


def _load_settings() -> dict:
    """Load settings.json."""
    if not SETTINGS_FILE.exists():
        return {}
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)


def _is_backup_enabled() -> bool:
    """Check if generation results backup is enabled in settings."""
    settings = _load_settings()
    return settings.get("backup", {}).get("generation_results_to_dropbox", False)


def _get_dropbox_credentials() -> Optional[dict]:
    """Load Dropbox credentials from .env file."""
    load_dotenv(ENV_FILE)
    
    client_id = os.getenv("DROPBOX_CLIENT_ID")
    client_secret = os.getenv("DROPBOX_CLIENT_SECRET")
    refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        return None
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }


def _get_access_token(credentials: dict) -> Optional[str]:
    """Get fresh Dropbox access token using refresh token."""
    try:
        response = requests.post(
            "https://api.dropboxapi.com/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": credentials["refresh_token"],
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
            },
            timeout=30,
        )
        
        if not response.ok:
            logger.warning(f"[Backup] Failed to get Dropbox token: {response.status_code}")
            return None
        
        return response.json().get("access_token")
        
    except requests.RequestException as e:
        logger.warning(f"[Backup] Dropbox token request failed: {e}")
        return None


def _create_zip(source_dir: Path, zip_path: Path) -> bool:
    """Create a zip file from source directory."""
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        return True
    except Exception as e:
        logger.error(f"[Backup] Failed to create zip: {e}")
        return False


def _upload_to_dropbox(token: str, file_path: Path, dropbox_path: str) -> bool:
    """Upload a file to Dropbox."""
    try:
        url = "https://content.dropboxapi.com/2/files/upload"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Dropbox-API-Arg": json.dumps({
                "path": dropbox_path,
                "mode": "overwrite",
            }),
            "Content-Type": "application/octet-stream",
        }
        
        with open(file_path, "rb") as f:
            response = requests.post(url, headers=headers, data=f, timeout=120)
        
        if response.ok:
            size_bytes = response.json().get("size", 0)
            logger.success(f"[Backup] Uploaded to Dropbox: {dropbox_path} ({size_bytes} bytes)")
            return True
        else:
            logger.warning(f"[Backup] Dropbox upload failed: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        logger.warning(f"[Backup] Dropbox upload request failed: {e}")
        return False


def backup_generation_results() -> bool:
    """
    Backup generation_results/ folder to Dropbox as a dated zip.
    
    Returns:
        True if backup succeeded or was intentionally skipped
        False if backup was attempted but failed
    """
    # Check if backup is enabled
    if not _is_backup_enabled():
        logger.debug("[Backup] Generation results backup disabled in settings")
        return True
    
    logger.info("[Backup] Starting generation results backup...")
    
    # Check for Dropbox credentials
    credentials = _get_dropbox_credentials()
    if credentials is None:
        logger.warning(
            "[Backup] Dropbox credentials missing in .env. "
            "Skipping backup. Required: DROPBOX_CLIENT_ID, DROPBOX_CLIENT_SECRET, DROPBOX_REFRESH_TOKEN"
        )
        return True  # Continue pipeline, just skip backup
    
    # Check if generation_results folder exists
    if not GENERATION_RESULTS_DIR.exists():
        logger.warning(f"[Backup] generation_results/ not found, skipping")
        return True
    
    # Check if folder has content
    files = list(GENERATION_RESULTS_DIR.rglob('*'))
    if not files:
        logger.warning("[Backup] generation_results/ is empty, skipping")
        return True
    
    # Get access token
    token = _get_access_token(credentials)
    if token is None:
        logger.warning("[Backup] Could not obtain Dropbox token, skipping backup")
        return True
    
    # Create dated zip file
    today_str = date.today().isoformat()
    zip_filename = f"generation_results_{today_str}.zip"
    zip_path = PROJECT_ROOT / zip_filename
    
    logger.info(f"[Backup] Creating {zip_filename}...")
    if not _create_zip(GENERATION_RESULTS_DIR, zip_path):
        return False
    
    # Upload to Dropbox
    dropbox_path = f"{DROPBOX_FOLDER}/{zip_filename}"
    success = _upload_to_dropbox(token, zip_path, dropbox_path)
    
    # Clean up local zip file
    try:
        zip_path.unlink()
        logger.debug(f"[Backup] Cleaned up local zip file")
    except Exception as e:
        logger.warning(f"[Backup] Failed to delete local zip: {e}")
    
    return success
