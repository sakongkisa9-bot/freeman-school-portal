"""
Cython setup script for Freeman School Portal
Compiles Python files to C extensions for additional security
"""

from distutils.core import setup
from Cython.Build import cythonize
import os
import sys

# Core application files to compile with Cython
CORE_FILES = [
    'main.py',
    'ui_dashboard.py',
    'security.py',
    'license_manager.py',
    'database.py',
    'grading_logic.py',
]

# UI marksheet files to compile
MARKSHEET_FILES = [
    'ui_marksheet_playgroup.py',
    'ui_marksheet_pp1.py',
    'ui_marksheet_pp2.py',
    'ui_marksheet_lower.py',
    'ui_marksheet_primary.py',
    'ui_marksheet_junior.py',
    'ui_summary.py',
]

# Service files to compile
SERVICE_FILES = [
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

# All files to compile
ALL_FILES = CORE_FILES + MARKSHEET_FILES + SERVICE_FILES

# Filter files that actually exist
EXISTING_FILES = [f for f in ALL_FILES if os.path.exists(f)]

print(f"Found {len(EXISTING_FILES)} Python files to compile with Cython")

# Cython compilation options
CYTHON_DIRECTIVES = {
    'language_level': 3,
    'embedsignature': False,  # Hide function signatures
    'binding': False,  # Disable Python-C API binding
}

def build_cython():
    """Build Cython extensions"""
    print("Starting Cython compilation...")
    
    setup(
        name='FreemanSchoolPortal',
        ext_modules=cythonize(
            EXISTING_FILES,
            compiler_directives=CYTHON_DIRECTIVES,
            annotate=False,  # Set to True to generate HTML annotation files
            force=True
        ),
        script_args=['build_ext', '--inplace']
    )
    
    print("Cython compilation complete!")

if __name__ == "__main__":
    build_cython()
