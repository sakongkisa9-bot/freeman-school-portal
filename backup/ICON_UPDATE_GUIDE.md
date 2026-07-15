# Manual Icon Replacement Guide (No Rebuild Required)

## Overview
This guide shows how to replace the icon in an existing executable without rebuilding the entire application.

## Files Created
- `freeman_icon_round.png` - Preview image of the new round icon
- `freeman_icon_round.ico` - Multi-size ICO file for executable icon

## Method 1: Using Resource Hacker (Recommended)

### Step 1: Download Resource Hacker
1. Go to: http://www.angusj.com/resourcehacker/
2. Download and install Resource Hacker

### Step 2: Replace Icon in Executable
1. Open Resource Hacker
2. File → Open → Select `FreemanSchoolPortal_Secure.exe`
3. In the left tree view, expand "Icon" folder
4. You'll see icon resources (usually numbered like 101, 102, etc.)
5. Right-click on the main icon resource → "Replace Icon..."
6. Select `freeman_icon_round.ico`
7. Click "Replace"
8. File → Save As → Save as `FreemanSchoolPortal_Secure.exe` (overwrite existing)

### Step 3: Clear Windows Icon Cache
1. Close Resource Hacker
2. Run the provided batch file: `clear_icon_cache.bat`
3. Or manually:
   - Open Task Manager
   - End "Windows Explorer" process
   - Delete: `C:\Users\<Username>\AppData\Local\IconCache.db`
   - Restart Windows Explorer

## Method 2: Using Custom Patcher (For Distribution)

### Create a Simple Icon Patcher Script
```python
import pefile
import os

def replace_icon(exe_path, new_icon_path):
    """Replace icon in executable using pefile"""
    try:
        pe = pefile.PE(exe_path)
        
        # This is a simplified example
        # Full icon replacement requires complex PE manipulation
        # Consider using Resource Hacker for reliable results
        
        print("Icon replacement requires PE file manipulation")
        print("Use Resource Hacker for reliable icon replacement")
        
    except Exception as e:
        print(f"Error: {e}")

# Usage:
# replace_icon("FreemanSchoolPortal_Secure.exe", "freeman_icon_round.ico")
```

## Method 3: Using IconChanger (Alternative Tool)

### Step 1: Download IconChanger
1. Search for "IconChanger" online
2. Download and install

### Step 2: Replace Icon
1. Open IconChanger
2. Select `FreemanSchoolPortal_Secure.exe`
3. Choose `freeman_icon_round.ico`
4. Apply changes

## Distribution as Update

### For End Users:
1. Send these files to users:
   - `freeman_icon_round.ico` (new icon)
   - `ICON_UPDATE_GUIDE.md` (this guide)
   - `Resource Hacker portable` (optional, for easy replacement)

2. Instructions for users:
   - Close the Freeman School Portal application
   - Follow the Resource Hacker instructions above
   - Clear icon cache
   - Restart the application

### Automated Update Script (Advanced)
Create a batch script that users can run:

```batch
@echo off
echo Freeman School Portal Icon Update
echo =================================
echo.
echo This script will update the application icon.
echo Please close the Freeman School Portal before continuing.
echo.
pause

REM Check if Resource Hacker is available
if not exist "ResourceHacker.exe" (
    echo ERROR: Resource Hacker not found!
    echo Please download Resource Hacker from: http://www.angusj.com/resourcehacker/
    echo Place ResourceHacker.exe in the same folder as this script.
    pause
    exit /b 1
)

REM Replace icon
ResourceHacker.exe -open FreemanSchoolPortal_Secure.exe -save FreemanSchoolPortal_Secure.exe -action addoverwrite -res freeman_icon_round.ico -mask ICONGROUP,MAIN,

if %ERRORLEVEL% EQU 0 (
    echo Icon replaced successfully!
    echo.
    echo Clearing icon cache...
    taskkill /f /im explorer.exe
    del /f /q "%LOCALAPPDATA%\IconCache.db"
    start explorer.exe
    echo.
    echo Icon update complete! Please restart the application.
) else (
    echo ERROR: Icon replacement failed!
)

pause
```

## Important Notes

### Windows Icon Caching
- Windows caches icons aggressively
- Even after replacement, the old icon may appear
- Clearing the icon cache is essential
- Sometimes requires a system restart

### Icon Format Requirements
- ICO file must be multi-size (16, 32, 48, 64, 128, 256)
- The created `freeman_icon_round.ico` meets these requirements
- Round icons work fine in Windows - they appear with transparent backgrounds

### Backup
- Always backup the original executable before modification
- Keep a copy of the original `FreemanSchoolPortal_Secure.exe`

### Testing
- After replacement, test on different Windows versions
- Check icon appearance in:
  - File Explorer
  - Taskbar
  - Desktop shortcut
  - Alt+Tab switcher

## Troubleshooting

### Icon Not Changing
1. Clear icon cache (run `clear_icon_cache.bat`)
2. Restart computer
3. Check if icon was properly embedded (open with Resource Hacker)

### Resource Hacker Errors
1. Ensure executable is not running
2. Run Resource Hacker as Administrator
3. Check file permissions

### Icon Appears Distorted
1. Ensure ICO file has all required sizes
2. Re-create the ICO with proper size specifications
3. Test the ICO file by setting it as a desktop icon first

## Summary

**Files to distribute:**
- `freeman_icon_round.ico` (new round icon)
- `ICON_UPDATE_GUIDE.md` (instructions)
- Optional: `Resource Hacker portable` (for easy replacement)

**User steps:**
1. Close application
2. Use Resource Hacker to replace icon
3. Clear icon cache
4. Restart application

**No rebuild required** - icon can be replaced in existing executable.
