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
        # Handle both development and executable environments
        if getattr(sys, 'frozen', False):
            # Running as executable
            BASE_DIR = sys._MEIPASS
            USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
            os.makedirs(USER_DATA_DIR, exist_ok=True)
            
            # Copy config files from bundled location to user data directory if they don't exist
            self._initialize_config_files(BASE_DIR, USER_DATA_DIR)
        else:
            # Running as script
            BASE_DIR = os.path.dirname(os.path.realpath(__file__))
            USER_DATA_DIR = BASE_DIR
        
        self.version_file = os.path.join(USER_DATA_DIR, "version.json")
        self.config_file = os.path.join(USER_DATA_DIR, "update_config.json")
        self.temp_dir = os.path.join(USER_DATA_DIR, "temp_updates")
        self.backup_dir = os.path.join(USER_DATA_DIR, "backup")
        self.current_version = self.get_current_version()
    
    def _initialize_config_files(self, bundled_dir, user_data_dir):
        """Copy config files from bundled location to user data directory if they don't exist"""
        config_files = ['update_config.json', 'version.json']
        
        for config_file in config_files:
            bundled_path = os.path.join(bundled_dir, config_file)
            user_path = os.path.join(user_data_dir, config_file)
 
            if not os.path.exists(user_path) and os.path.exists(bundled_path):
                try:
                    shutil.copy2(bundled_path, user_path)
                    print(f"[UpdateManager] Copied {config_file} from bundled to user data directory")
                except Exception as e:
                    print(f"[UpdateManager] Failed to copy {config_file}: {e}")
    
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
                    # Use download_url from server if available, otherwise construct default
                    download_url = remote_version_data.get("download_url")
                    if not download_url:
                        download_url = f"{update_url}freeman_update_{remote_version}.zip"
                    
                    return True, {
                        "current_version": self.current_version,
                        "new_version": remote_version,
                        "changelog": remote_version_data.get("changelog", ""),
                        "download_url": download_url
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
            os.makedirs(self.temp_dir, exist_ok=True)
            update_file = os.path.join(self.temp_dir, "update.zip")
            
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
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Get current directory - ALWAYS use USER_DATA_DIR for updates
            # When running as executable, sys._MEIPASS is read-only and temporary
            # Updates must go to user data directory which is writable
            if getattr(sys, 'frozen', False):
                # For executable, extract to user data directory
                extract_dir = self.version_file.replace("version.json", "").rstrip(os.sep)
            else:
                # For script, use current directory
                extract_dir = os.path.dirname(os.path.realpath(__file__))
            
            # Backup current files from extraction directory
            if os.path.exists(extract_dir):
                for item in os.listdir(extract_dir):
                    item_path = os.path.join(extract_dir, item)
                    if os.path.isfile(item_path) and not item.endswith('.db'):
                        shutil.copy2(item_path, os.path.join(self.backup_dir, item))
            
            # Extract update to the writable directory. Published packages may
            # contain an enclosing update_package directory.
            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                members = zip_ref.infolist()
                package_prefix = 'update_package/'
                wrapped_package = members and all(
                    member.filename == package_prefix
                    or member.filename.startswith(package_prefix)
                    for member in members
                )

                if wrapped_package:
                    for member in members:
                        member.filename = member.filename[len(package_prefix):]
                        if member.filename:
                            zip_ref.extract(member, extract_dir)
                else:
                    zip_ref.extractall(extract_dir)
            
            # Verify extraction by checking for key files
            print(f"[UpdateManager] Extracted files to: {extract_dir}")
            extracted_files = os.listdir(extract_dir)
            print(f"[UpdateManager] Files in extraction directory: {extracted_files[:10]}")
            
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
            
            # Restart the application automatically to apply updates
            self.restart_application()
            
            return True, "Update installed successfully. Restarting application..."
        except Exception as e:
            # Restore from backup if update failed
            try:
                if os.path.exists(self.backup_dir):
                    for item in os.listdir(self.backup_dir):
                        shutil.copy2(os.path.join(self.backup_dir, item), extract_dir)
            except:
                pass
            
            return False, f"Error installing update: {str(e)}"
    
    def load_config(self):
        """Load update configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def restart_application(self):
        """Restart the application to apply updates"""
        try:
            import subprocess
            import time
            
            # Create a flag file to indicate update is pending
            # This helps the new instance know to prioritize user data files
            flag_file = os.path.join(self.backup_dir, "update_pending.flag")
            with open(flag_file, 'w') as f:
                f.write("update_pending")
            
            if getattr(sys, 'frozen', False):
                # Running as executable - restart the executable
                executable = sys.executable
                if os.path.exists(executable):
                    # Use subprocess to restart the executable without shell
                    # This is more reliable on Windows
                    DETACHED_PROCESS = 0x00000008
                    subprocess.Popen(
                        [executable],
                        creationflags=DETACHED_PROCESS,
                        close_fds=True
                    )
                    # Give the new process time to start before exiting
                    time.sleep(1.0)
                    # Exit current instance
                    sys.exit(0)
            else:
                # Running as script - restart with Python
                script_path = os.path.realpath(__file__)
                subprocess.Popen(
                    [sys.executable, script_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
                    close_fds=True
                )
                time.sleep(1.0)
                sys.exit(0)
        except Exception as e:
            print(f"[UpdateManager] Error restarting application: {e}")

    def cleanup(self):
        """Clean up temporary files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass
