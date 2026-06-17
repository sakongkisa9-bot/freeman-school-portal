import requests
import json
import os
import zipfile
import shutil
import sys
from pathlib import Path


class UpdateManager:
    """Manages system updates for remote deployment"""
    
    def __init__(self):
        self.version_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "version.json"
        )
        self.current_version = self.get_current_version()
    
    def get_current_version(self):
        """Get current version from version.json"""
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, "r") as f:
                    data = json.load(f)
                    return data.get("version", "1.0.0")
        except Exception:
            pass
        return "1.0.0"
    
    def check_for_updates(self):
        """Check if updates are available from remote server"""
        try:
            config = self.load_config()
            update_url = config.get("update_url", "")
            
            if not update_url:
                return False, "Update URL not configured"
            
            # Fetch latest version info from server
            version_url = f"{update_url}version.json"
            response = requests.get(version_url, timeout=10)
            
            if response.status_code == 200:
                remote_version_data = response.json()
                remote_version = remote_version_data.get("version", "1.0.0")
                
                if self.is_newer_version(remote_version):
                    return True, {
                        "current_version": self.current_version,
                        "new_version": remote_version,
                        "changelog": remote_version_data.get("changelog", ""),
                        "download_url": f"{update_url}freeman_update_{remote_version}.zip"
                    }
                else:
                    return False, "System is up to date"
            else:
                return False, "Could not connect to update server"
                
        except Exception as e:
            return False, f"Error checking for updates: {str(e)}"
    
    def is_newer_version(self, remote_version):
        """Compare version strings to check if remote is newer"""
        try:
            current_parts = [int(x) for x in self.current_version.split(".")]
            remote_parts = [int(x) for x in remote_version.split(".")]
            
            for i in range(max(len(current_parts), len(remote_parts))):
                current = current_parts[i] if i < len(current_parts) else 0
                remote = remote_parts[i] if i < len(remote_parts) else 0
                
                if remote > current:
                    return True
                elif remote < current:
                    return False
            
            return False
        except Exception:
            return False
    
    def download_update(self, download_url, progress_callback=None):
        """Download update file from server"""
        try:
            response = requests.get(download_url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            
            # Create temp directory for download
            temp_dir = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "temp_updates"
            )
            os.makedirs(temp_dir, exist_ok=True)
            
            update_file = os.path.join(temp_dir, "update.zip")
            
            downloaded = 0
            with open(update_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                            progress_callback(progress)
            
            return True, update_file
        except Exception as e:
            return False, f"Error downloading update: {str(e)}"
    
    def install_update(self, update_file):
        """Install downloaded update"""
        try:
            # Create backup directory
            backup_dir = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "backup"
            )
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup current files
            current_dir = os.path.dirname(os.path.realpath(__file__))
            for item in os.listdir(current_dir):
                item_path = os.path.join(current_dir, item)
                if os.path.isfile(item_path) and not item.endswith('.db'):
                    shutil.copy2(item_path, os.path.join(backup_dir, item))
            
            # Extract update
            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                zip_ref.extractall(current_dir)
            
            # Update version file
            update_info = self.check_for_updates()
            if update_info[0]:  # If update available
                new_version = update_info[1]["new_version"]
                with open(self.version_file, "w") as f:
                    json.dump({
                        "version": new_version,
                        "release_date": "",
                        "update_url": self.load_config().get("update_url", ""),
                        "changelog": update_info[1].get("changelog", "")
                    }, f, indent=4)
            
            # Cleanup
            os.remove(update_file)
            
            return True, "Update installed successfully"
        except Exception as e:
            # Restore from backup if update failed
            try:
                current_dir = os.path.dirname(os.path.realpath(__file__))
                backup_dir = os.path.join(current_dir, "backup")
                for item in os.listdir(backup_dir):
                    shutil.copy2(os.path.join(backup_dir, item), current_dir)
            except:
                pass
            
            return False, f"Error installing update: {str(e)}"
    
    def load_config(self):
        """Load update configuration"""
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "update_config.json"
            )
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            temp_dir = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "temp_updates"
            )
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception:
            pass
