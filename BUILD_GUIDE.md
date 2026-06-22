# Freeman School Portal - Secure Build Guide

This guide explains how to create a secure executable using PyArmor, Cython, and PyInstaller.

## Prerequisites

All required packages have been installed:
- pyarmor (code obfuscation)
- cython (compilation to C)
- pyinstaller (executable creation)

## Build Modes

The build script (`build_secure.py`) supports four build modes:

### 1. Simple Build (Recommended for Testing)
```bash
python build_secure.py simple
```
- Uses PyInstaller only
- Fastest build time
- Basic protection
- Good for initial testing

### 2. PyArmor Build
```bash
python build_secure.py pyarmor
```
- Uses PyArmor + PyInstaller
- Code obfuscation
- Moderate protection
- Slower than simple build

### 3. Cython Build
```bash
python build_secure.py cython
```
- Uses Cython + PyInstaller
- Compiles Python to C extensions
- Strong protection
- May have compatibility issues

### 4. Full Security Build (Maximum Protection)
```bash
python build_secure.py full
```
- Uses PyArmor + Cython + PyInstaller
- Maximum security layering
- Slowest build time
- May have runtime issues

## Recommended Workflow

1. **Start with simple build** to ensure everything works:
   ```bash
   python build_secure.py simple
   ```

2. **Test the executable**:
   - Run `dist/FreemanSchoolPortal.exe`
   - Verify all features work correctly
   - Check for missing files or dependencies

3. **If simple build works**, try PyArmor build:
   ```bash
   python build_secure.py pyarmor
   ```

4. **Test again** to ensure obfuscation didn't break anything

5. **For maximum security**, try full build:
   ```bash
   python build_secure.py full
   ```

## Files Included in Build

The build script includes these data files:
- `assets/` - Images and splash screens
- `templates/` - HTML templates for web portal
- `static/` - Static files for web portal
- `school_config.json` - School configuration
- `notification_config.json` - Notification settings
- `update_config.json` - Update server settings
- `version.json` - Version information
- `mpesa_config.json` - M-Pesa payment settings

## Protected Files

The following Python files are protected:
- Core: `main.py`, `ui_dashboard.py`, `security.py`, `license_manager.py`, `database.py`, `grading_logic.py`
- UI: All marksheet UI files (`ui_marksheet_*.py`, `ui_summary.py`)
- Services: `cloud_service.py`, `cloud_portal_v2.py`, `notification_service.py`, `fcm_service.py`, `mpesa_service.py`, `update_manager.py`, `newsletter.py`, `network_manager.py`, `hotspot_server.py`, `teachers_linked.py`, `reportforms.py`, `wizard.py`, `splash.py`

## Troubleshooting

### Missing Dependencies
If the executable fails to run due to missing dependencies:
1. Check the console output for missing module warnings
2. Add the missing module to the `hidden_imports` list in `build_secure.py`
3. Rebuild the executable

### Path Issues
The application is designed to handle both development and executable environments:
- Database and config files are stored in `~/FreemanSchoolPortal/`
- Assets are bundled with the executable
- Templates and static files are included

### PyArmor Issues
If PyArmor obfuscation causes issues:
1. Try the simple build first to isolate the problem
2. Check PyArmor logs for specific file failures
3. Some files may need to be excluded from obfuscation

### Cython Issues
If Cython compilation fails:
1. Cython may not support all Python features used
2. Dynamic imports and `eval()` calls may cause issues
3. Consider using PyArmor-only build instead

## Output

After successful build, the executable will be at:
```
dist/FreemanSchoolPortal.exe
```

## Security Notes

- **Simple build**: Basic protection, code is bundled but readable
- **PyArmor build**: Code obfuscation makes reverse engineering difficult
- **Cython build**: Compiled to C, very difficult to reverse engineer
- **Full build**: Multiple layers of protection, maximum security

For production distribution, the PyArmor build is recommended as it provides good protection with minimal compatibility issues.
