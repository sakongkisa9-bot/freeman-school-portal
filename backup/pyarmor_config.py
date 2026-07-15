"""
PyArmor Configuration for Freeman School Portal
This configuration defines which files to obfuscate and protection settings
"""

import os
from pyarmor.cli import main as pyarmor_main

# Core application files to obfuscate
CORE_FILES = [
    "main.py",
    "ui_dashboard.py",
    "security.py",
    "license_manager.py",
    "database.py",
    "grading_logic.py",
]

# UI marksheet files to obfuscate
MARKSHEET_FILES = [
    "ui_marksheet_playgroup.py",
    "ui_marksheet_pp1.py",
    "ui_marksheet_pp2.py",
    "ui_marksheet_lower.py",
    "ui_marksheet_primary.py",
    "ui_marksheet_junior.py",
    "ui_summary.py",
]

# Service files to obfuscate
SERVICE_FILES = [
    "cloud_service.py",
    "cloud_portal_v2.py",
    "notification_service.py",
    "fcm_service.py",
    "mpesa_service.py",
    "update_manager.py",
    "newsletter.py",
    "network_manager.py",
    "hotspot_server.py",
    "teachers_linked.py",
    "reportforms.py",
    "wizard.py",
    "splash.py",
]

# All files to protect
ALL_FILES = CORE_FILES + MARKSHEET_FILES + SERVICE_FILES

# PyArmor protection options
PYARMOR_OPTIONS = [
    "--obf-code",  # Obfuscate code
    "--obf-mod",  # Obfuscate module names
    "--mix-rstr",  # Mix string literals
    "--restrict",  # Add runtime restrictions
    "--wrap",  # Wrap Python files
]

# Output directory for obfuscated files
OUTPUT_DIR = "dist/obfuscated"


def obfuscate_files():
    """Obfuscate all Python files using PyArmor"""
    print("Starting PyArmor obfuscation...")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Initialize PyArmor project
    pyarmor_main(["init", "--src", ".", "--entry", "main.py", OUTPUT_DIR])

    # Obfuscate each file
    for file in ALL_FILES:
        if os.path.exists(file):
            print(f"Obfuscating {file}...")
            try:
                pyarmor_main(["gen", "--output", OUTPUT_DIR, file])
            except Exception as e:
                print(f"Error obfuscating {file}: {e}")

    print(f"PyArmor obfuscation complete. Output in {OUTPUT_DIR}")


if __name__ == "__main__":
    obfuscate_files()
