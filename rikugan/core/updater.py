"""Auto-update mechanism for Rikugan.

Checks for updates from GitHub and provides one-click update functionality.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..core.config import RikuganConfig
from ..core.errors import ProviderError
from ..core.logging import log_debug, log_error, log_info, log_warn


@dataclass
class UpdateInfo:
    """Update information."""

    current_version: str
    latest_version: str
    download_url: str
    changelog: list[str]
    min_compatible_version: str
    update_required: bool
    is_newer: bool


class Updater:
    """Rikugan auto-updater.

    Checks for updates from GitHub and handles the update process.
    """

    UPDATE_URL = "https://raw.githubusercontent.com/alicangnll/Rikugan/main/update.json"
    BACKUP_DIR = ".rikugan_backup"

    def __init__(self):
        """Initialize updater."""
        self.config = RikuganConfig()
        self.current_version = self._get_current_version()

    def _get_current_version(self) -> str:
        """Get current Rikugan version."""
        # Try to get from constants
        try:
            from ..constants import PLUGIN_VERSION
            return PLUGIN_VERSION
        except ImportError:
            pass

        # Try to get from config
        if hasattr(self.config, "version"):
            return self.config.version

        # Fallback to hardcoded version
        return "1.2.2"

    def check_for_updates(self, timeout: int = 10) -> Optional[UpdateInfo]:
        """Check for updates from GitHub.

        Args:
            timeout: Request timeout in seconds.

        Returns:
            UpdateInfo if update available, None otherwise.
        """
        try:
            log_info("Checking for updates...")
            log_debug(f"Fetching update info from {self.UPDATE_URL}")

            request = urllib.request.Request(
                self.UPDATE_URL,
                headers={"User-Agent": f"Rikugan/{self.current_version}"}
            )

            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode())

            latest_version = data.get("version", self.current_version)
            download_url = data.get("download_url", "")
            changelog = data.get("changelog", [])
            min_compatible = data.get("min_compatible_version", "1.0.0")
            update_required = data.get("update_required", False)

            is_newer = self._compare_versions(latest_version, self.current_version) > 0

            update_info = UpdateInfo(
                current_version=self.current_version,
                latest_version=latest_version,
                download_url=download_url,
                changelog=changelog,
                min_compatible_version=min_compatible,
                update_required=update_required,
                is_newer=is_newer,
            )

            if is_newer:
                log_info(f"Update available: {self.current_version} → {latest_version}")
                for item in changelog:
                    log_debug(f"  - {item}")
            else:
                log_info("Already up to date")

            return update_info

        except urllib.error.URLError as e:
            log_error(f"Failed to check for updates: {e}")
            return None
        except Exception as e:
            log_error(f"Error checking for updates: {e}")
            return None

    def download_update(self, update_info: UpdateInfo, dest_dir: Optional[Path] = None) -> Optional[Path]:
        """Download update package.

        Args:
            update_info: Update information.
            dest_dir: Destination directory. If None, uses temp directory.

        Returns:
            Path to downloaded file, or None if download failed.
        """
        try:
            if dest_dir is None:
                dest_dir = Path(tempfile.gettempdir())
            else:
                dest_dir = Path(dest_dir)

            dest_dir.mkdir(parents=True, exist_ok=True)
            download_path = dest_dir / "rikugan_update.zip"

            log_info(f"Downloading update from {update_info.download_url}")

            request = urllib.request.Request(
                update_info.download_url,
                headers={"User-Agent": f"Rikugan/{self.current_version}"}
            )

            with urllib.request.urlopen(request, timeout=300) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0

                with open(download_path, "wb") as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            log_debug(f"Download progress: {progress:.1f}%")

            log_info(f"Downloaded to {download_path}")
            return download_path

        except Exception as e:
            log_error(f"Failed to download update: {e}")
            return None

    def backup_installation(self) -> bool:
        """Backup current installation.

        Returns:
            True if backup successful, False otherwise.
        """
        try:
            backup_path = Path(self.BACKUP_DIR)
            backup_path.mkdir(parents=True, exist_ok=True)

            # Backup current directory
            current_dir = Path(__file__).parent.parent.parent
            if current_dir.name == "rikugan":
                # We're in the package directory
                source_dir = current_dir.parent
            else:
                # We're in the repository root
                source_dir = current_dir

            backup_name = f"backup_{self.current_version}"
            backup_file = backup_path / f"{backup_name}.tar.gz"

            log_info(f"Creating backup: {backup_file}")

            subprocess.run(
                ["tar", "-czf", str(backup_file), "-C", str(source_dir.parent),
                    source_dir.name],
                check=True,
                capture_output=True,
            )

            log_info("Backup created successfully")
            return True

        except Exception as e:
            log_error(f"Failed to create backup: {e}")
            return False

    def install_update(self, download_path: Path) -> bool:
        """Install update package.

        Args:
            download_path: Path to downloaded update package.

        Returns:
            True if installation successful, False otherwise.
        """
        try:
            log_info("Installing update...")

            # Create backup
            if not self.backup_installation():
                log_warn("Backup failed, proceeding anyway")

            # Extract update
            extract_dir = download_path.parent / "extracted"
            extract_dir.mkdir(exist_ok=True)

            log_info("Extracting update package...")
            with zipfile.ZipFile(download_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find Rikugan directory in extracted package
            extracted_root = extract_dir
            for root in extract_dir.iterdir():
                if (root / "rikugan_plugin.py").exists():
                    extracted_root = root
                    break

            # Copy files to current installation
            current_dir = Path(__file__).parent.parent.parent
            if current_dir.name == "rikugan":
                source_dir = current_dir.parent
            else:
                source_dir = current_dir

            log_info(f"Installing to {source_dir}...")

            # Copy rikugan directory
            rikugan_src = extracted_root / "rikugan"
            if rikugan_src.exists():
                rikugan_dst = source_dir / "rikugan"
                self._copy_directory(rikugan_src, rikugan_dst)

            # Copy plugin file
            plugin_src = extracted_root / "rikugan_plugin.py"
            if plugin_src.exists():
                import shutil
                shutil.copy2(plugin_src, source_dir / "rikugan_plugin.py")

            # Copy update.json
            update_src = extracted_root / "update.json"
            if update_src.exists():
                import shutil
                shutil.copy2(update_src, source_dir / "update.json")

            log_info("Update installed successfully")
            log_info("Please restart IDA Pro/Binary Ninja for changes to take effect")

            return True

        except Exception as e:
            log_error(f"Failed to install update: {e}")
            log_error("You can restore from backup if needed")
            return False

    def _copy_directory(self, src: Path, dst: Path) -> None:
        """Copy directory recursively.

        Args:
            src: Source directory.
            dst: Destination directory.
        """
        import shutil

        if dst.exists():
            shutil.rmtree(dst)

        shutil.copytree(src, dst)

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings.

        Args:
            v1: First version.
            v2: Second version.

        Returns:
            Positive if v1 > v2, negative if v1 < v2, 0 if equal.
        """
        def parse_version(v: str) -> tuple[int, ...]:
            return tuple(map(int, v.split(".")))

        v1_parts = parse_version(v1)
        v2_parts = parse_version(v2)

        # Pad shorter version with zeros
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts = v1_parts + (0,) * (max_len - len(v1_parts))
        v2_parts = v2_parts + (0,) * (max_len - len(v2_parts))

        if v1_parts > v2_parts:
            return 1
        elif v1_parts < v2_parts:
            return -1
        else:
            return 0

    def restore_backup(self) -> bool:
        """Restore from backup.

        Returns:
            True if restoration successful, False otherwise.
        """
        try:
            backup_path = Path(self.BACKUP_DIR)
            backups = list(backup_path.glob("backup_*.tar.gz"))

            if not backups:
                log_error("No backups found")
                return False

            # Use the most recent backup
            latest_backup = max(backups, key=lambda p: p.stat().st_mtime)

            log_info(f"Restoring from {latest_backup}")

            current_dir = Path(__file__).parent.parent.parent
            if current_dir.name == "rikugan":
                source_dir = current_dir.parent
            else:
                source_dir = current_dir

            # Extract backup
            subprocess.run(
                ["tar", "-xzf", str(latest_backup), "-C", str(source_dir.parent)],
                check=True,
                capture_output=True,
            )

            log_info("Backup restored successfully")
            log_info("Please restart IDA Pro/Binary Ninja")
            return True

        except Exception as e:
            log_error(f"Failed to restore backup: {e}")
            return False


def check_for_updates() -> Optional[UpdateInfo]:
    """Check for Rikugan updates.

    Returns:
        UpdateInfo if update available, None otherwise.
    """
    updater = Updater()
    return updater.check_for_updates()


def install_update(update_info: UpdateInfo) -> bool:
    """Install Rikugan update.

    Args:
        update_info: Update information.

    Returns:
        True if installation successful, False otherwise.
    """
    updater = Updater()

    # Download update
    download_path = updater.download_update(update_info)
    if download_path is None:
        return False

    # Install update
    return updater.install_update(download_path)


def restore_backup() -> bool:
    """Restore Rikugan from backup.

    Returns:
        True if restoration successful, False otherwise.
    """
    updater = Updater()
    return updater.restore_backup()
