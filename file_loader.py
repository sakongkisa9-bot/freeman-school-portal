"""
File Loader Utility
Handles loading files with correct priority for executable vs script environments
When running as executable, prioritizes user data directory over bundled files
"""

import os
import sys
import shutil
import ast
import importlib.util
from importlib.machinery import ModuleSpec
import logging

logging.info("=" * 60)
logging.info("FILE_LOADER.PY - MODULE IMPORTED")
logging.info("=" * 60)
logging.info(f"FileLoader imported from: {__file__}")
logging.info(f"sys.frozen: {getattr(sys, 'frozen', False)}")
if getattr(sys, 'frozen', False):
    logging.info(f"sys._MEIPASS: {sys._MEIPASS}")
logging.info("=" * 60)


def get_app_directories():
    """
    Returns the base directories for the application
    """
    if getattr(sys, 'frozen', False):
        # Running as executable
        bundled_dir = sys._MEIPASS
        user_data_dir = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal")
        os.makedirs(user_data_dir, exist_ok=True)
        logging.info(f"get_app_directories - Executable mode:")
        logging.info(f"  bundled_dir: {bundled_dir}")
        logging.info(f"  user_data_dir: {user_data_dir}")
    else:
        # Running as script
        bundled_dir = os.path.dirname(os.path.realpath(__file__))
        user_data_dir = bundled_dir
        logging.info(f"get_app_directories - Script mode:")
        logging.info(f"  bundled_dir: {bundled_dir}")
        logging.info(f"  user_data_dir: {user_data_dir}")

    return bundled_dir, user_data_dir


def get_file_path(relative_path, prefer_user_data=True):
    """
    Get the full path to a file with correct priority
    
    Args:
        relative_path: Relative path from base directory (e.g., "ui_dashboard.py")
        prefer_user_data: If True, prioritize user data directory when running as executable
    
    Returns:
        Full path to the file
    """
    bundled_dir, user_data_dir = get_app_directories()
    
    if getattr(sys, 'frozen', False) and prefer_user_data:
        # For executable, check user data directory first
        user_path = os.path.join(user_data_dir, relative_path)
        if os.path.exists(user_path):
            return user_path
        
        # Fall back to bundled directory
        bundled_path = os.path.join(bundled_dir, relative_path)
        if os.path.exists(bundled_path):
            return bundled_path
    else:
        # For script or when preferring bundled, use bundled directory
        bundled_path = os.path.join(bundled_dir, relative_path)
        if os.path.exists(bundled_path):
            return bundled_path
    
    # If not found, return the user data path (for new files from updates)
    return os.path.join(user_data_dir, relative_path)


def initialize_user_data_files():
    """
    Copy essential files from bundled directory to user data directory
    This should be called on first run or when needed
    """
    bundled_dir, user_data_dir = get_app_directories()
    
    if not getattr(sys, 'frozen', False):
        return  # Not needed for script mode
    
    # Files to copy to user data directory
    files_to_copy = [
        'update_config.json',
        'version.json',
        'school_config.json',
        'notification_config.json',
        'mpesa_config.json'
    ]
    
    for filename in files_to_copy:
        bundled_path = os.path.join(bundled_dir, filename)
        user_path = os.path.join(user_data_dir, filename)
        
        if not os.path.exists(user_path) and os.path.exists(bundled_path):
            try:
                shutil.copy2(bundled_path, user_path)
                print(f"[FileLoader] Copied {filename} to user data directory")
            except Exception as e:
                print(f"[FileLoader] Failed to copy {filename}: {e}")


def get_updated_module_path(module_name):
    """
    Get the path to a Python module, prioritizing updated versions in user data
    
    Args:
        module_name: Name of the module (e.g., "ui_dashboard")
    
    Returns:
        Path to the module file
    """
    # Try .py file
    py_path = get_file_path(f"{module_name}.py")
    if os.path.exists(py_path):
        return py_path
    
    # Try compiled version if needed
    return None


def sync_updated_files():
    """
    Ensure updated files from user data directory are available
    This can be called after an update to ensure files are in the right place
    """
    bundled_dir, user_data_dir = get_app_directories()
    
    if not getattr(sys, 'frozen', False):
        return  # Not needed for script mode
    
    # Updated modules are resolved by CustomImportHook after API validation.
    while user_data_dir in sys.path:
        sys.path.remove(user_data_dir)
    
    # Also ensure bundled dir is in path (but after user data)
    if bundled_dir not in sys.path:
        sys.path.append(bundled_dir)
    
    print(f"[FileLoader] Bundled dir: {bundled_dir}")
    print(f"[FileLoader] User data dir: {user_data_dir}")
    print("[FileLoader] User-data modules will be loaded only after API validation")
    print(f"[FileLoader] Current sys.path: {sys.path[:3]}")
    
    # Install custom import hook for PyInstaller compatibility
    install_custom_import_hook(user_data_dir, bundled_dir)


class CustomImportHook:
    """
    Custom import hook to prioritize updated modules from user data directory
    This is necessary because PyInstaller has its own import mechanism
    """

    def __init__(self, user_data_dir, bundled_dir):
        self.user_data_dir = user_data_dir
        self.bundled_dir = bundled_dir

    @staticmethod
    def _module_definitions(path):
        try:
            with open(path, "r", encoding="utf-8") as source_file:
                tree = ast.parse(source_file.read(), filename=path)
        except (OSError, SyntaxError, UnicodeError) as error:
            return None, f"cannot parse override: {error}"

        functions = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        classes = {
            node.name: {
                method.name: method
                for method in node.body
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }
        return (functions, classes), None

    @classmethod
    def _validate_override(cls, module_name, path):
        definitions, error = cls._module_definitions(path)
        if error:
            return error

        functions, classes = definitions
        required_methods = {
            "cloud_service": {
                "CloudService": (
                    "create_exam",
                    "set_period",
                    "start_new_year",
                    "upload_cba_tasks",
                    "fetch_cbc_ratings",
                    "fetch_cbc_covered_strands",
                    "fetch_cba_results",
                ),
            },
            "teachers_linked": {"TeachersLinkedView": ("__init__",)},
            "ui_marksheet_junior": {"JuniorMarkSheetView": ("__init__",)},
            "ui_marksheet_primary": {"PrimaryMarkSheetView": ("__init__",)},
            "ui_marksheet_lower": {"LowerMarkSheetView": ("__init__",)},
            "ui_marksheet_playgroup": {"PlaygroupMarkSheetView": ("__init__",)},
            "ui_marksheet_pp1": {"PP1MarkSheetView": ("__init__",)},
            "ui_marksheet_pp2": {"PP2MarkSheetView": ("__init__",)},
        }.get(module_name, {})

        missing = []
        for class_name, methods in required_methods.items():
            class_methods = classes.get(class_name, {})
            for method_name in methods:
                method = class_methods.get(method_name)
                if method is None:
                    missing.append(f"{class_name}.{method_name}")
                    continue
                if module_name != "cloud_service":
                    parameters = {arg.arg for arg in method.args.args + method.args.kwonlyargs}
                    if "stream" not in parameters and method.args.kwarg is None:
                        missing.append(f"{class_name}.{method_name}(stream=...)")

        if module_name == "cloud_service":
            for function_name in ("ask_cloud_credentials", "apply_cloud_records_to_table"):
                if function_name not in functions:
                    missing.append(function_name)

        if missing:
            return "missing required API: " + ", ".join(missing)
        return None

    def find_spec(self, fullname, path, target=None):
        """
        Find module spec, prioritizing user data directory
        """
        # Skip standard library and third-party packages
        if fullname.startswith(('tkinter', 'PIL', 'customtkinter', 'sqlite3',
                               'flask', 'werkzeug', 'requests', 'firebase_admin',
                               'fpdf', 'reportlab', 'json', 'os', 'sys', 'shutil',
                               'pathlib', 'importlib', 'subprocess', 'time',
                               'cv2', 'numpy', 'pytesseract')):
            return None

        # Skip PyInstaller bootstrap modules
        if fullname.startswith('_pyi_'):
            return None

        # Try to find .py file in user data directory
        module_file = fullname.replace('.', os.sep) + '.py'
        user_path = os.path.join(self.user_data_dir, module_file)

        if os.path.exists(user_path):
            compatibility_error = self._validate_override(fullname, user_path)
            if compatibility_error:
                logging.warning(
                    "Ignoring incompatible user module %s at %s: %s",
                    fullname,
                    user_path,
                    compatibility_error,
                )
                return None
            logging.info(f"[CustomImportHook] Loading {fullname} from user data: {user_path}")
            try:
                spec = importlib.util.spec_from_file_location(fullname, user_path)
                logging.info(f"[CustomImportHook] Successfully loaded {fullname} from user data")
                return spec
            except Exception as e:
                logging.error(f"[CustomImportHook] Error loading {fullname}: {e}")
                return None

        return None


def install_custom_import_hook(user_data_dir, bundled_dir):
    """
    Install custom import hook to prioritize user data directory
    """
    try:
        hook = CustomImportHook(user_data_dir, bundled_dir)
        sys.meta_path.insert(0, hook)
        print(f"[FileLoader] Custom import hook installed for module priority")
    except Exception as e:
        print(f"[FileLoader] Failed to install custom import hook: {e}")


def force_reload_module(module_name):
    """
    Force reload a module from user data directory if available
    Use this after updates to ensure new code is loaded
    """
    if module_name in sys.modules:
        # Remove from sys.modules to force reload
        del sys.modules[module_name]
        print(f"[FileLoader] Removed {module_name} from sys.modules for reload")
    
    # Re-import the module
    import importlib
    try:
        module = importlib.import_module(module_name)
        print(f"[FileLoader] Reloaded {module_name} successfully")
        return module
    except Exception as e:
        print(f"[FileLoader] Failed to reload {module_name}: {e}")
        return None
