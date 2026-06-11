"""
Test script to verify license blocking mechanism
This simulates a different hardware ID to test the blocking
"""
import json
import os
from license_manager import LicenseManager

def test_license_blocking():
    print("=== Testing License Blocking Mechanism ===\n")
    
    # Get current license info
    manager = LicenseManager()
    current_license = manager.get_license_info()
    
    if current_license:
        print(f"Current License Hardware ID: {current_license['hardware_id']}")
        print(f"Current System Hardware ID: {manager.hardware_id}")
        print(f"Match: {current_license['hardware_id'] == manager.hardware_id}\n")
        
        # Test 1: Valid license (should pass)
        is_valid, message = manager.validate_license()
        print(f"Test 1 - Valid License Check:")
        print(f"  Result: {'PASS' if is_valid else 'FAIL'}")
        print(f"  Message: {message}\n")
        
        # Test 2: Simulate different hardware ID (should fail)
        print("Test 2 - Simulating Different Hardware:")
        # Temporarily modify the license file to have a different hardware ID
        license_file = manager.license_file
        
        # Backup current license
        with open(license_file, 'r') as f:
            original_license = json.load(f)
        
        # Create fake hardware ID
        fake_hardware_id = "00000000000000000000000000000000"
        original_license['hardware_id'] = fake_hardware_id
        
        # Write modified license
        with open(license_file, 'w') as f:
            json.dump(original_license, f, indent=4)
        
        # Test validation with fake hardware ID
        is_valid_fake, message_fake = manager.validate_license()
        print(f"  Result: {'PASS (blocked correctly)' if not is_valid_fake else 'FAIL (should have been blocked)'}")
        print(f"  Message: {message_fake}\n")
        
        # Restore original license
        with open(license_file, 'w') as f:
            json.dump(original_license, f, indent=4)
        
        # Restore correct hardware ID
        original_license['hardware_id'] = manager.hardware_id
        with open(license_file, 'w') as f:
            json.dump(original_license, f, indent=4)
        
        print("Test 3 - Restored License Check:")
        is_valid_restored, message_restored = manager.validate_license()
        print(f"  Result: {'PASS' if is_valid_restored else 'FAIL'}")
        print(f"  Message: {message_restored}\n")
        
        print("=== All Tests Completed ===")
        
    else:
        print("No license file found. Run license_manager.py first to generate license.")

if __name__ == "__main__":
    test_license_blocking()
