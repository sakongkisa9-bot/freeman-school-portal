"""
Direct PyArmor Obfuscation Script
This script properly obfuscates Python files using PyArmor CLI
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Configuration
PROJECT_DIR = Path(__file__).parent
OBFUSCATED_DIR = PROJECT_DIR / "dist_obfuscated"
PYARMOR_PATH = Path("C:/Users/HomePC/AppData/Local/Python/pythoncore-3.14-64/Scripts/pyarmor.exe")

# Files to obfuscate - ALL Python files in the project
FILES_TO_OBFUSCATE = [
    'main.py',
    'ui_dashboard.py',
    'security.py',
    'license_manager.py',
    'database.py',
    'grading_logic.py',
    'ui_marksheet_playgroup.py',
    'ui_marksheet_pp1.py',
    'ui_marksheet_pp2.py',
    'ui_marksheet_lower.py',
    'ui_marksheet_primary.py',
    'ui_marksheet_junior.py',
    'ui_summary.py',
    'cloud_service.py',
    'cloud_portal_v2.py',
    'notification_service.py',
    'fcm_service.py',
    'mpesa_service.py',
    'update_manager.py',
    'newsletter.py',
    'network_manager.py',
    'hotspot_server.py',
    'teachers_linked.py',
    'reportforms.py',
    'wizard.py',
    'splash.py',
    'ocr_student_dialog.py',
    'ocr_service.py',
    # Additional utility files
    'pyarmor_config.py',
]

def clean_obfuscated_dir():
    """Clean obfuscated directory"""
    if OBFUSCATED_DIR.exists():
        try:
            shutil.rmtree(OBFUSCATED_DIR)
        except PermissionError:
            print("ERROR: Cannot clean obfuscated directory. The executable may still be running.")
            print("Please close the executable and try again.")
            sys.exit(1)
    OBFUSCATED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Cleaned and created {OBFUSCATED_DIR}")

def copy_project_files():
    """Copy all project files to obfuscated directory"""
    print("Copying project files to obfuscated directory...")
    
    # Copy Python files
    for file in FILES_TO_OBFUSCATE:
        src = PROJECT_DIR / file
        if src.exists():
            shutil.copy2(src, OBFUSCATED_DIR / file)
            print(f"  Copied {file}")
    
    # Copy essential directories and files
    items_to_copy = [
        "assets",
        "templates", 
        "static",
        "tesseract",
        # Config files
        "school_config.json",
        "notification_config.json",
        "update_config.json",
        "version.json",
        "mpesa_config.json",
        # Icon files
        "freeman_icon.ico",
        "freeman_icon.png",
        "freeman_icon_round.ico",
        "freeman_icon_round.png",
        # Firebase config (if exists)
        "firebase-service-account.json",
    ]
    
    for item in items_to_copy:
        src = PROJECT_DIR / item
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, OBFUSCATED_DIR / item)
            else:
                shutil.copy2(src, OBFUSCATED_DIR / item)
            print(f"  Copied {item}")

def run_pyarmor_obfuscation():
    """Run PyArmor obfuscation"""
    print("\n=== Running PyArmor Obfuscation ===")
    
    # Change to obfuscated directory
    os.chdir(OBFUSCATED_DIR)
    
    try:
        # Use PyArmor project-based obfuscation to handle dependencies
        print("Initializing PyArmor project...")
        result = subprocess.run(
            [str(PYARMOR_PATH), "init", "--src", ".", "main.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"PyArmor init failed: {result.stderr}")
            print("Trying simple obfuscation approach...")
            # Fall back to simple obfuscation without project init
            return simple_obfuscation()
        
        print("PyArmor project initialized successfully")
        
        # Obfuscate the entire project at once
        print("Obfuscating project files...")
        result = subprocess.run(
            [str(PYARMOR_PATH), "gen", "--output", "dist_obfuscated", "main.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Project obfuscation failed: {result.stderr}")
            print("Falling back to simple obfuscation...")
            return simple_obfuscation()
        
        print("Project obfuscation completed!")
        return True
        
    except Exception as e:
        print(f"Error during PyArmor obfuscation: {e}")
        print("Falling back to simple obfuscation...")
        return simple_obfuscation()
    finally:
        # Change back to project directory
        os.chdir(PROJECT_DIR)

def simple_obfuscation():
    """Simple obfuscation without project initialization"""
    print("\n=== Running Simple PyArmor Obfuscation ===")
    
    os.chdir(OBFUSCATED_DIR)
    
    try:
        # Obfuscate files that don't have complex dependencies first
        # NOTE: Exclude files with file path handling, complex imports, or used by UI modules
        simple_files = [
            'license_manager.py',
            'security.py', 
            # 'database.py',  # EXCLUDED - imports notification_service, PyArmor breaks import handling
            # 'grading_logic.py',  # EXCLUDED - used by marksheet files, PyArmor breaks import handling
            # 'cloud_service.py',  # EXCLUDED - used by marksheet files, PyArmor breaks import handling
            # 'notification_service.py',  # EXCLUDED - PyArmor breaks path handling
            'fcm_service.py',
            'mpesa_service.py',
            'update_manager.py',
            'network_manager.py',
            'hotspot_server.py',
            'teachers_linked.py',
            'wizard.py',
        ]
        
        print("Obfuscating independent modules...")
        for file in simple_files:
            if (OBFUSCATED_DIR / file).exists():
                print(f"  Obfuscating {file}...")
                result = subprocess.run(
                    [str(PYARMOR_PATH), "gen", "-O", ".", file],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"    {file} obfuscated successfully")
                else:
                    print(f"    Skipped {file}")
        
        # Don't obfuscate files with complex import dependencies
        # These will be protected by PyInstaller only
        complex_files = [
            'main.py',
            'ui_dashboard.py',
            'splash.py',
            'ui_marksheet_playgroup.py',
            'ui_marksheet_pp1.py',
            'ui_marksheet_pp2.py',
            'ui_marksheet_lower.py',
            'ui_marksheet_primary.py',
            'ui_marksheet_junior.py',
            'ui_summary.py',
            'cloud_portal_v2.py',
            'newsletter.py',
            'reportforms.py',
        ]
        
        print("\nSkipping complex dependency files (protected by PyInstaller):")
        for file in complex_files:
            if (OBFUSCATED_DIR / file).exists():
                print(f"  - {file}")
        
        print("\nPyArmor obfuscation completed (partial)!")
        print("Complex files protected by PyInstaller bundling only.")
        return True
        
    except Exception as e:
        print(f"Error during simple obfuscation: {e}")
        return False
    finally:
        os.chdir(PROJECT_DIR)

def create_obfuscated_executable():
    """Create executable from obfuscated files"""
    print("\n=== Creating Executable from Obfuscated Files ===")
    
    os.chdir(OBFUSCATED_DIR)
    
    try:
        # PyInstaller command for obfuscated files
        pyinstaller_cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name", "FreemanSchoolPortal_Secure",
            "--icon", "freeman_icon.ico",
            "--clean",
        ]
        
        # Add data files
        data_files = [
            ("assets", "assets"),
            ("templates", "templates"),
            ("static", "static"),
            ("school_config.json", "."),
            ("notification_config.json", "."),
            ("update_config.json", "."),
            ("version.json", "."),
            ("mpesa_config.json", "."),
            ("tesseract", "tesseract"),
        ]
        
        for src, dst in data_files:
            src_path = OBFUSCATED_DIR / src
            if src_path.exists():
                pyinstaller_cmd.extend(["--add-data", f"{src};{dst}"])
        
        # Add hidden imports - include ALL modules
        hidden_imports = [
            "customtkinter",
            "PIL",
            "sqlite3",
            "flask",
            "werkzeug",
            "requests",
            "firebase_admin",
            "grading_logic",
            "license_manager",
            "security",
            "database",
            "pytesseract",
            "cv2",
            "ocr_student_dialog",
            "ocr_service",
            "cloud_service",
            "cloud_portal_v2",
            "notification_service",
            "fcm_service",
            "mpesa_service",
            "update_manager",
            "newsletter",
            "network_manager",
            "hotspot_server",
            "teachers_linked",
            "reportforms",
            "wizard",
            "splash",
            "ui_marksheet_playgroup",
            "ui_marksheet_pp1",
            "ui_marksheet_pp2",
            "ui_marksheet_lower",
            "ui_marksheet_primary",
            "ui_marksheet_junior",
            "ui_summary",
        ]
        
        for imp in hidden_imports:
            pyinstaller_cmd.extend(["--hidden-import", imp])
        
        # Add entry point
        pyinstaller_cmd.append("main.py")
        
        print("Running PyInstaller on obfuscated files...")
        result = subprocess.run(pyinstaller_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"PyInstaller failed: {result.stderr}")
            return False
        
        print("Executable created successfully!")
        print(f"Location: {OBFUSCATED_DIR / 'dist' / 'FreemanSchoolPortal_Secure.exe'}")
        return True
        
    except Exception as e:
        print(f"Error creating executable: {e}")
        return False
    finally:
        os.chdir(PROJECT_DIR)

def main():
    """Main function"""
    print("=" * 60)
    print("PyArmor Obfuscation Script")
    print("=" * 60)
    
    # Clean and prepare
    clean_obfuscated_dir()
    
    # Copy files
    copy_project_files()
    
    # Obfuscate with PyArmor
    success = run_pyarmor_obfuscation()
    
    if success:
        # Create executable
        create_obfuscated_executable()
        print("\n" + "=" * 60)
        print("Secure obfuscated build complete!")
        print("=" * 60)
    else:
        print("\nPyArmor obfuscation failed. Check the error messages above.")

if __name__ == "__main__":
    main()
