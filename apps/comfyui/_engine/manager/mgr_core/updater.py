"""
ContextUp Update Manager
Checks for updates via GitHub Releases API and handles update process.
"""

import json
import logging
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable, Tuple

logger = logging.getLogger("updater")

# GitHub Repository Info
GITHUB_OWNER = "simiroa"
GITHUB_REPO = "CONTEXTUP"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

@dataclass
class UpdateInfo:
    """Information about an available update."""
    current_version: str
    latest_version: str
    release_notes: str
    download_url: str
    published_at: str
    is_newer: bool


class UpdateChecker:
    """Handles checking for and applying updates."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir) if not isinstance(root_dir, Path) else root_dir
        self.version_file = self.root_dir / "version.json"
        self._cached_update: Optional[UpdateInfo] = None
        self._check_in_progress = False
        
    def get_current_version(self) -> str:
        """Read current version from version.json."""
        try:
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get("version", "0.0.0")
        except Exception as e:
            logger.error(f"Failed to read version: {e}")
        return "0.0.0"
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.
        Returns: 1 if v1 > v2, -1 if v1 < v2, 0 if equal
        """
        def parse(v):
            # Remove 'v' prefix if present
            v = v.lstrip('vV')
            parts = []
            for p in v.split('.'):
                try:
                    parts.append(int(p))
                except ValueError:
                    parts.append(0)
            return parts
        
        p1, p2 = parse(v1), parse(v2)
        
        # Pad shorter version with zeros
        max_len = max(len(p1), len(p2))
        p1.extend([0] * (max_len - len(p1)))
        p2.extend([0] * (max_len - len(p2)))
        
        for a, b in zip(p1, p2):
            if a > b:
                return 1
            elif a < b:
                return -1
        return 0
    
    def check_for_updates(self, callback: Optional[Callable[[Optional[UpdateInfo]], None]] = None):
        """
        Check GitHub for the latest release (async).
        Calls callback with UpdateInfo if update available, None otherwise.
        """
        if self._check_in_progress:
            return
        
        def _check():
            self._check_in_progress = True
            result = None
            
            try:
                # Create request with User-Agent (required by GitHub API)
                req = urllib.request.Request(
                    GITHUB_API_URL,
                    headers={
                        'User-Agent': 'ContextUp-Updater/1.0',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                
                latest_version = data.get('tag_name', '0.0.0').lstrip('vV')
                current_version = self.get_current_version()
                
                is_newer = self._compare_versions(latest_version, current_version) > 0
                
                # Parse release notes
                body = data.get('body', '')
                release_notes = self._parse_release_notes(body)
                
                # Get download URL (prefer zip)
                download_url = ""
                for asset in data.get('assets', []):
                    if asset.get('name', '').endswith('.zip'):
                        download_url = asset.get('browser_download_url', '')
                        break
                
                # Fallback to zipball URL
                if not download_url:
                    download_url = data.get('zipball_url', '')
                
                result = UpdateInfo(
                    current_version=current_version,
                    latest_version=latest_version,
                    release_notes=release_notes,
                    download_url=download_url,
                    published_at=data.get('published_at', ''),
                    is_newer=is_newer
                )
                
                self._cached_update = result
                logger.info(f"Update check complete: current={current_version}, latest={latest_version}, newer={is_newer}")
                
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    logger.info("No releases found on GitHub")
                elif e.code == 403:
                    logger.warning("GitHub API rate limit exceeded")
                else:
                    logger.error(f"GitHub API error: {e}")
            except urllib.error.URLError as e:
                logger.warning(f"Network error checking for updates: {e}")
            except Exception as e:
                logger.error(f"Update check failed: {e}")
            finally:
                self._check_in_progress = False
                
            if callback:
                callback(result)
        
        threading.Thread(target=_check, daemon=True).start()
    
    def _parse_release_notes(self, body: str) -> str:
        """Parse and clean up release notes markdown."""
        if not body:
            return "No release notes available."
        
        # Limit length for display
        lines = body.strip().split('\n')
        if len(lines) > 10:
            lines = lines[:10]
            lines.append("...")
        
        return '\n'.join(lines)
    
    def get_cached_update(self) -> Optional[UpdateInfo]:
        """Return cached update info without making API call."""
        return self._cached_update
    
    def perform_update(self, callback: Optional[Callable[[bool, str], None]] = None):
        """
        Perform the update using git pull or ZIP download.
        Calls callback with (success: bool, message: str).
        """
        def _update():
            success = False
            message = ""
            
            try:
                # Check if .git exists (prefer git pull)
                git_dir = self.root_dir / ".git"
                
                if git_dir.exists():
                    success, message = self._update_via_git()
                else:
                    success, message = self._update_via_download()
                    
            except Exception as e:
                message = f"Update failed: {e}"
                logger.error(message)
            
            if callback:
                callback(success, message)
        
        threading.Thread(target=_update, daemon=True).start()
    
    def _update_via_git(self) -> Tuple[bool, str]:
        """Update using git pull."""
        try:
            logger.info("Performing git pull...")
            
            result = subprocess.run(
                ["git", "pull", "--rebase"],
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info(f"Git pull successful: {result.stdout}")
                return True, "Update successful! Please restart the application."
            else:
                logger.error(f"Git pull failed: {result.stderr}")
                return False, f"Git pull failed: {result.stderr}"
                
        except FileNotFoundError:
            return False, "Git is not installed or not in PATH."
        except subprocess.TimeoutExpired:
            return False, "Git pull timed out."
        except Exception as e:
            return False, f"Git error: {e}"
    
    def _update_via_download(self) -> Tuple[bool, str]:
        """Update by downloading ZIP from GitHub."""
        if not self._cached_update or not self._cached_update.download_url:
            return False, "No download URL available."
        
        # For safety, just open the download page in browser
        import webbrowser
        release_url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
        webbrowser.open(release_url)
        
        return True, "Opened download page in browser. Please download and extract manually."
