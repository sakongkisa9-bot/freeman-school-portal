# Step-by-Step Update Deployment Guide

## Overview
Complete guide to deploying updates using your existing UpdateManager system.

## Prerequisites
- Access to your update server (web server with file hosting)
- Updated files ready to distribute
- Admin access to update_config.json

## Step 1: Prepare Updated Files

### 1.1 Identify Files to Update
List all files that have changed:
- Python files with bug fixes
- Configuration files
- Icon files
- Assets
- New features

### 1.2 Test Updated Files Locally
- Run the application with updated files
- Verify all functionality works
- Test both script and executable modes

### 1.3 Create Update Package Structure
```
update_package/
├── main.py (if updated)
├── ui_dashboard.py (if updated)
├── security.py (if updated)
├── freeman_icon.ico (if updated)
├── school_config.json (if updated)
└── [other updated files]
```

## Step 2: Create Update ZIP File

### 2.1 Create Package Directory
```bash
mkdir update_package
```

### 2.2 Copy Updated Files
```bash
# Example: Copy updated files
copy main.py update_package\
copy ui_dashboard.py update_package\
copy freeman_icon.ico update_package\
```

### 2.3 Create ZIP File
```bash
cd update_package
powershell Compress-Archive -Path * -DestinationPath ..\freeman_update_1.0.1.zip
```

### 2.4 Verify ZIP Contents
```bash
# Check ZIP contents
powershell Expand-Archive -Path freeman_update_1.0.1.zip -DestinationPath test_extract
dir test_extract
```

## Step 3: Update Version Information

### 3.1 Update Local version.json
```json
{
  "version": "1.0.1",
  "release_date": "2026-06-18",
  "update_url": "https://your-server.com/updates/",
  "changelog": "Bug fixes and improvements"
}
```

### 3.2 Update Server version.json
Create or update the version.json on your update server:
```json
{
  "version": "1.0.1",
  "release_date": "2026-06-18",
  "changelog": "Updated application with bug fixes and new features",
  "download_url": "https://your-server.com/updates/freeman_update_1.0.1.zip"
}
```

## Step 4: Upload to Update Server

### 4.1 Upload Update ZIP
```bash
# Using FTP (example)
ftp your-server.com
put freeman_update_1.0.1.zip /updates/
```

### 4.2 Upload version.json
```bash
# Upload version.json to server root or updates folder
put version.json /updates/
```

### 4.3 Verify Files are Accessible
Test URLs in browser:
- `https://your-server.com/updates/freeman_update_1.0.1.zip`
- `https://your-server.com/updates/version.json`

## Step 5: Configure Update URL

### 5.1 Check update_config.json
```json
{
  "update_url": "https://your-server.com/updates/"
}
```

### 5.2 Update update_config.json if Needed
```python
import json
import os

config_path = os.path.join(os.path.expanduser("~"), "FreemanSchoolPortal", "update_config.json")
config = {
    "update_url": "https://your-server.com/updates/"
}

with open(config_path, "w") as f:
    json.dump(config, f, indent=4)
```

## Step 6: Test Update Process

### 6.1 Local Testing
1. Set update_config.json to point to test server
2. Run application
3. Trigger manual update check
4. Verify update downloads and installs
5. Restart application
6. Verify updated functionality

### 6.2 Test Update Manager
```python
from update_manager import UpdateManager

manager = UpdateManager()
has_update, info = manager.check_for_updates()
print(f"Has update: {has_update}")
print(f"Update info: {info}")

if has_update:
    success, file_path = manager.download_update(info['download_url'])
    if success:
        success, result = manager.install_update(file_path)
        print(f"Install result: {result}")
```

## Step 7: Deploy to Production

### 7.1 Final Verification
- All files uploaded correctly
- URLs are accessible
- version.json has correct version
- Changelog is accurate

### 7.2 Monitor First Updates
- Watch for user feedback
- Check update success rates
- Monitor error logs

## Step 8: Rollback Plan (If Needed)

### 8.1 Restore Previous Version
If update fails:
1. Revert version.json to previous version
2. Remove or rename bad update ZIP
3. Users will no longer see update notification

### 8.2 Hotfix Update
If critical bug found:
1. Fix the issue
2. Create new update package (e.g., 1.0.2)
3. Follow same deployment steps
4. Users will get hotfix automatically

## Example: Icon Update Deployment

### Step 1: Prepare Icon Files
```bash
# Copy round icon
copy freeman_icon_round.ico update_package\freeman_icon.ico
```

### Step 2: Create Update Package
```bash
cd update_package
powershell Compress-Archive -Path freeman_icon.ico -DestinationPath ..\freeman_update_1.0.1.zip
```

### Step 3: Update Server version.json
```json
{
  "version": "1.0.1",
  "release_date": "2026-06-18",
  "changelog": "Updated application icon to round shape (same design)",
  "download_url": "https://your-server.com/updates/freeman_update_1.0.1.zip"
}
```

### Step 4: Upload and Test
```bash
# Upload files
ftp your-server.com
put freeman_update_1.0.1.zip /updates/
put version.json /updates/

# Test URL in browser
# https://your-server.com/updates/freeman_update_1.0.1.zip
# https://your-server.com/updates/version.json
```

## Example: Code Fix Deployment

### Step 1: Prepare Updated Files
```bash
copy main.py update_package\
copy security.py update_package\
```

### Step 2: Create Update Package
```bash
cd update_package
powershell Compress-Archive -Path * -DestinationPath ..\freeman_update_1.0.2.zip
```

### Step 3: Update Server version.json
```json
{
  "version": "1.0.2",
  "release_date": "2026-06-18",
  "changelog": "Fixed login authentication and path handling issues",
  "download_url": "https://your-server.com/updates/freeman_update_1.0.2.zip"
}
```

## Important Notes

### Version Numbering
- Use semantic versioning: MAJOR.MINOR.PATCH
- Increment PATCH for bug fixes (1.0.0 → 1.0.1)
- Increment MINOR for new features (1.0.0 → 1.1.0)
- Increment MAJOR for breaking changes (1.0.0 → 2.0.0)

### Changelog Best Practices
- Be clear and specific about changes
- Mention bug fixes and new features
- Include upgrade instructions if needed
- Keep it user-friendly

### File Safety
- Never include database files in updates
- Never include user-specific config files
- Only include application files
- Test updates on clean installations

### Backup Safety
- Your UpdateManager automatically backs up files
- Backups stored in `~/FreemanSchoolPortal/backup/`
- Failed updates restore from backup automatically
- Keep backups for rollback capability

## Troubleshooting

### Update Not Detected
- Check update_config.json has correct URL
- Verify version.json on server is accessible
- Ensure server version is higher than local version
- Check network connectivity

### Download Fails
- Verify download URL is correct
- Check file permissions on server
- Ensure ZIP file is not corrupted
- Test URL in browser

### Installation Fails
- Check file permissions in application directory
- Verify disk space is available
- Check if application is running (close it first)
- Review error logs in UpdateManager

### Icon Not Changing
- Clear Windows icon cache
- Restart computer
- Verify icon file was replaced
- Check icon cache clearing in update process

## Quick Reference

### Update Checklist
- [ ] Updated files tested locally
- [ ] Update package created
- [ ] ZIP file verified
- [ ] version.json updated
- [ ] Files uploaded to server
- [ ] URLs tested in browser
- [ ] update_config.json configured
- [ ] Update tested locally
- [ ] Rollback plan prepared

### Common Commands
```bash
# Create update package
mkdir update_package
copy [files] update_package\
cd update_package
powershell Compress-Archive -Path * -DestinationPath ..\freeman_update_X.X.X.zip

# Test update
python -c "from update_manager import UpdateManager; m = UpdateManager(); print(m.check_for_updates())"

# Clear icon cache
taskkill /f /im explorer.exe
del %LOCALAPPDATA%\IconCache.db
explorer.exe
```

## Summary

**Your path pattern is correct for bundled files**, but use separate pattern for user-writable files.

**Update deployment steps:**
1. Prepare updated files
2. Create update ZIP package
3. Update version.json on server
4. Upload files to update server
5. Configure update URL
6. Test update process
7. Deploy to production
8. Monitor and support

Your existing UpdateManager handles the rest automatically!
