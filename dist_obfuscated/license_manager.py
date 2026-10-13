"""
License Manager for Freeman School Portal
Locks the application to a specific computer using hardware identification
"""
import os
import json
import hashlib
import platform
import subprocess
import uuid
from datetime import datetime


class LicenseManager:
    def __init__(self):
        self.project_dir = os.path.dirname(os.path.realpath(__file__))
        self.license_file = os.path.join(self.project_dir, '.license_key')
        self.hardware_id = self._get_hardware_id()
        
    def _get_hardware_id(self):
        """
        Generate a unique hardware ID based on motherboard serial and MAC address
        This provides a reliable identifier that's difficult to change
        """
        try:
            # Get motherboard serial number (Windows)
            if platform.system() == 'Windows':
                try:
                    result = subprocess.run(['wmic', 'baseboard', 'get', 'serialnumber'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if 'SerialNumber' not in line and line.strip():
                                motherboard_serial = line.strip()
                                break
                        else:
                            motherboard_serial = "UNKNOWN"
                    else:
                        motherboard_serial = "UNKNOWN"
                except:
                    motherboard_serial = "UNKNOWN"
            else:
                motherboard_serial = "UNKNOWN"
            
            # Get MAC address of first network interface
            try:
                mac = uuid.getnode()
                mac_address = ':'.join(['{:02x}'.format((mac >> elements) & 0xff) 
                                       for elements in range(0,8*6,8)][::-1])
            except:
                mac_address = "UNKNOWN"
            
            # Combine and hash to create a unique but consistent ID
            combined = f"{motherboard_serial}_{mac_address}_{platform.machine()}"
            hardware_id = hashlib.sha256(combined.encode()).hexdigest()[:32]
            
            return hardware_id
            
        except Exception as e:
            print(f"Error generating hardware ID: {e}")
            # Fallback to simple UUID if hardware detection fails
            return str(uuid.uuid4())[:32]
    
    def _get_machine_info(self):
        """Get detailed machine information for display"""
        info = {
            "platform": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hardware_id": self.hardware_id,
            "capture_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Try to get motherboard serial for display
        if platform.system() == 'Windows':
            try:
                result = subprocess.run(['wmic', 'baseboard', 'get', 'serialnumber'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'SerialNumber' not in line and line.strip():
                            info["motherboard_serial"] = line.strip()
                            break
            except:
                pass
        
        return info
    
    def generate_license(self):
        """
        Generate a new license file for the current computer
        This should only be called once when first installing on a new computer
        """
        if os.path.exists(self.license_file):
            raise Exception("License file already exists. Cannot generate new license.")
        
        license_data = {
            "hardware_id": self.hardware_id,
            "machine_info": self._get_machine_info(),
            "license_created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "license_status": "ACTIVE",
            "activation_count": 1
        }
        
        with open(self.license_file, 'w') as f:
            json.dump(license_data, f, indent=4)
        
        return True
    
    def validate_license(self):
        """
        Validate that the current computer matches the licensed hardware
        Returns: (is_valid, message)
        """
        # If no license file exists, this is a first-time installation
        if not os.path.exists(self.license_file):
            return (False, "No license file found. First-time installation required.")
        
        try:
            with open(self.license_file, 'r') as f:
                license_data = json.load(f)
            
            licensed_hardware_id = license_data.get('hardware_id')
            
            # Check if current hardware matches licensed hardware
            if self.hardware_id == licensed_hardware_id:
                return (True, "License valid. Hardware matches.")
            else:
                return (False, f"License invalid. This software is licensed to a different computer.\n\n"
                              f"Licensed Hardware ID: {licensed_hardware_id}\n"
                              f"Current Hardware ID: {self.hardware_id}")
                
        except Exception as e:
            return (False, f"Error reading license file: {e}")
    
    def get_license_info(self):
        """Get current license information for display"""
        if not os.path.exists(self.license_file):
            return None
        
        try:
            with open(self.license_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def revoke_license(self):
        """
        Revoke the current license (useful for testing or legitimate re-installation)
        This should be protected and not easily accessible to end users
        """
        if os.path.exists(self.license_file):
            os.remove(self.license_file)
            return True
        return False


def check_and_activate_license():
    """
    Main function to check license status and handle activation
    Returns: (is_allowed, message)
    """
    manager = LicenseManager()
    
    # Check if license exists
    is_valid, message = manager.validate_license()
    
    if is_valid:
        return (True, "License validated successfully")
    elif "No license file found" in message:
        # First-time installation - generate license
        try:
            manager.generate_license()
            return (True, "License activated successfully for this computer")
        except Exception as e:
            return (False, f"Failed to activate license: {e}")
    else:
        # License exists but hardware doesn't match
        return (False, message)


if __name__ == "__main__":
    # Test the license manager
    manager = LicenseManager()
    print(f"Current Hardware ID: {manager.hardware_id}")
    print(f"Machine Info: {json.dumps(manager._get_machine_info(), indent=2)}")
    
    # Check license status
    is_allowed, message = check_and_activate_license()
    print(f"\nLicense Check: {is_allowed}")
    print(f"Message: {message}")
    
    # Display license info if exists
    license_info = manager.get_license_info()
    if license_info:
        print(f"\nLicense Info: {json.dumps(license_info, indent=2)}")
