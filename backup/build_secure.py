"""
Secure Build Script for Freeman School Portal
Combines PyArmor obfuscation, Cython compilation, and PyInstaller packaging
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Configuration
PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"
OBFUSCATED_DIR = OUTPUT_DIR / "obfuscated"

# Files and directories to include in the executable
DATA_FILES = [
    ("assets", "assets"),
    ("templates", "templates"),
    ("static", "static"),
    ("school_config.json", "."),
    ("notification_config.json", "."),
    ("update_config.json", "."),
    ("version.json", "."),
    ("mpesa_config.json", "."),
]

# Main entry point
ENTRY_POINT = "main.py"

def clean_build_dirs():
    """Clean previous build directories"""
    print("Cleaning previous build directories...")
    
    dirs_to_clean = [BUILD_DIR, OUTPUT_DIR]
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Removed {dir_path}")
    
    # Clean Cython compiled files
    for file in PROJECT_DIR.glob("*.so"):
        file.unlink()
        print(f"Removed {file}")
    
    for file in PROJECT_DIR.glob("*.c"):
        file.unlink()
        print(f"Removed {file}")
    
    print("Clean complete!")

def run_pyarmor():
    """Run PyArmor obfuscation"""
    print("\n=== Step 1: PyArmor Obfuscation ===")
    
    # List of files to obfuscate
    files_to_obfuscate = [
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
    ]
    
    # Filter existing files
    existing_files = [f for f in files_to_obfuscate if (PROJECT_DIR / f).exists()]
    
    print(f"Obfuscating {len(existing_files)} files with PyArmor...")
    
    # Create obfuscated directory
    OBFUSCATED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Copy files to obfuscated directory first
    for file in existing_files:
        src = PROJECT_DIR / file
        dst = OBFUSCATED_DIR / file
        shutil.copy2(src, dst)
        print(f"Copied {file} to obfuscated directory")
    
    # Run PyArmor on the obfuscated directory
    try:
        # Initialize PyArmor project
        subprocess.run([
            sys.executable, "-m", "pyarmor", "init",
            "--src", str(OBFUSCATED_DIR),
            "--entry", ENTRY_POINT,
            str(OBFUSCATED_DIR)
        ], check=True, cwd=PROJECT_DIR)
        
        # Obfuscate all files
        for file in existing_files:
            try:
                subprocess.run([
                    sys.executable, "-m", "pyarmor", "gen",
                    "--output", str(OBFUSCATED_DIR),
                    str(OBFUSCATED_DIR / file)
                ], check=True, cwd=PROJECT_DIR)
                print(f"Obfuscated {file}")
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to obfuscate {file}: {e}")
        
        print("PyArmor obfuscation complete!")
        
    except subprocess.CalledProcessError as e:
        print(f"PyArmor obfuscation failed: {e}")
        print("Continuing without PyArmor...")

def run_cython():
    """Run Cython compilation"""
    print("\n=== Step 2: Cython Compilation ===")
    
    # Files to compile with Cython
    files_to_compile = [
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
    ]
    
    # Filter existing files
    existing_files = [str(f) for f in files_to_compile if (PROJECT_DIR / f).exists()]
    
    print(f"Compiling {len(existing_files)} files with Cython...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "cython",
            "--directive", "language_level=3",
            "--directive", "embedsignature=False",
            *existing_files
        ], check=True, cwd=PROJECT_DIR)
        
        print("Cython compilation complete!")
        
    except subprocess.CalledProcessError as e:
        print(f"Cython compilation failed: {e}")
        print("Continuing without Cython...")

def run_pyinstaller():
    """Run PyInstaller to create executable"""
    print("\n=== Step 3: PyInstaller Packaging ===")
    
    # Build PyInstaller command
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "FreemanSchoolPortal",
        "--icon", "freeman_icon.ico",
        "--clean",
    ]
    
    # Add data files
    for src, dst in DATA_FILES:
        src_path = PROJECT_DIR / src
        if src_path.exists():
            pyinstaller_cmd.extend(["--add-data", f"{src};{dst}"])
            print(f"Adding data file: {src}")
    
    # Add hidden imports (common issues with PyInstaller)
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
    ]
    
    for imp in hidden_imports:
        pyinstaller_cmd.extend(["--hidden-import", imp])
    
    # Add entry point
    pyinstaller_cmd.append(ENTRY_POINT)
    
    print("Running PyInstaller...")
    print(f"Command: {' '.join(pyinstaller_cmd)}")
    
    try:
        subprocess.run(pyinstaller_cmd, check=True, cwd=PROJECT_DIR)
        print("PyInstaller packaging complete!")
        print(f"Executable created at: {OUTPUT_DIR / 'FreemanSchoolPortal.exe'}")
        
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed: {e}")
        sys.exit(1)

def build_simple():
    """Simple build without PyArmor/Cython (for testing)"""
    print("\n=== Simple Build (PyInstaller Only) ===")
    
    # Build PyInstaller command
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "FreemanSchoolPortal",
        "--icon", "freeman_icon.ico",
        "--clean",
    ]
    
    # Add data files
    for src, dst in DATA_FILES:
        src_path = PROJECT_DIR / src
        if src_path.exists():
            pyinstaller_cmd.extend(["--add-data", f"{src};{dst}"])
            print(f"Adding data file: {src}")
    
    # Add hidden imports
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
    ]
    
    for imp in hidden_imports:
        pyinstaller_cmd.extend(["--hidden-import", imp])
    
    # Add entry point
    pyinstaller_cmd.append(ENTRY_POINT)
    
    print("Running PyInstaller...")
    print(f"Command: {' '.join(pyinstaller_cmd)}")
    
    try:
        subprocess.run(pyinstaller_cmd, check=True, cwd=PROJECT_DIR)
        print("PyInstaller packaging complete!")
        print(f"Executable created at: {OUTPUT_DIR / 'FreemanSchoolPortal.exe'}")
        
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed: {e}")
        sys.exit(1)

def main():
    """Main build function"""
    print("=" * 60)
    print("Freeman School Portal - Secure Build Script")
    print("=" * 60)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = "simple"  # Default to simple build
    
    print(f"\nBuild mode: {mode}")
    
    # Clean previous builds
    clean_build_dirs()
    
    if mode == "full":
        # Full security build with PyArmor + Cython + PyInstaller
        run_pyarmor()
        run_cython()
        run_pyinstaller()
    elif mode == "pyarmor":
        # PyArmor + PyInstaller
        run_pyarmor()
        run_pyinstaller()
    elif mode == "cython":
        # Cython + PyInstaller
        run_cython()
        run_pyinstaller()
    else:
        # Simple PyInstaller only (recommended for testing)
        build_simple()
    
    print("\n" + "=" * 60)
    print("Build complete!")
    print("=" * 60)
    print(f"\nExecutable location: {OUTPUT_DIR / 'FreemanSchoolPortal.exe'}")
    print("\nBuild modes:")
    print("  python build_secure.py simple   - PyInstaller only (fastest)")
    print("  python build_secure.py pyarmor   - PyArmor + PyInstaller")
    print("  python build_secure.py cython    - Cython + PyInstaller")
    print("  python build_secure.py full     - PyArmor + Cython + PyInstaller (slowest)")

if __name__ == "__main__":
    main()
