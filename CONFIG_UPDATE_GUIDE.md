# Configuration Update Guide for Executable

## The Issue

When you edit configuration files in the project directory, the executable doesn't reflect your changes because it loads configuration from a different location.

## How Configuration Loading Works

### When Running as Script (Development)
- Config files are loaded from: Project directory
- Location: `c:\Users\HomePC\Documents\FreemanTech_Project\school_config.json`
- Changes to project files are immediately reflected

### When Running as Executable (Production)
- Config files are loaded from: User data directory
- Location: `C:\Users\<Username>\FreemanSchoolPortal\school_config.json`
- Changes to project files are NOT reflected
- Bundled config files are copied to user data directory on first run only

## Configuration File Locations

### Project Directory (Development)
```
c:\Users\HomePC\Documents\FreemanTech_Project\
├── school_config.json
├── notification_config.json
├── update_config.json
├── mpesa_config.json
└── version.json
```

### User Data Directory (Executable Runtime)
```
C:\Users\<Username>\FreemanSchoolPortal\
├── school_config.json
├── notification_config.json
├── update_config.json
├── mpesa_config.json
├── freeman_data.db
├── archives\
└── logs\
```

## How to Update Configuration

### Option 1: Edit User Data Directory Files (Recommended for Testing)

1. Navigate to: `C:\Users\<Username>\FreemanSchoolPortal\`
2. Edit the config files directly in this directory
3. Restart the executable
4. Changes will be reflected immediately

**Example:**
```
C:\Users\HomePC\FreemanSchoolPortal\school_config.json
```

### Option 2: Delete User Data Directory (Fresh Start)

1. Close the executable
2. Delete: `C:\Users\<Username>\FreemanSchoolPortal\`
3. Run the executable again
4. It will recreate the directory with bundled config files
5. Your changes from project files will now be reflected

**Warning:** This will delete all user data including:
- Database file (freeman_data.db)
- All student records
- All exam data
- Archives

### Option 3: Rebuild Executable (For Production Distribution)

1. Edit config files in project directory
2. Rebuild executable: `python obfuscate_pyarmor.py`
3. Delete user data directory on target machine
4. Run new executable

## Configuration Priority

The executable uses this priority:
1. **User Data Directory** (highest priority) - if exists, use this
2. **Bundled Files** (fallback) - if user data doesn't exist, copy from bundle
3. **Default Values** (last resort) - hardcoded defaults in code

## Common Configuration Files

### school_config.json
```json
{
    "school_name": "Your School Name",
    "system_username": "admin",
    "system_password": "your_password",
    "installation_fee": 5000,
    "amount_per_student": 100,
    "trial_days": 120,
    "premium_days": 120
}
```

### mpesa_config.json
```json
{
    "consumer_key": "your_key",
    "consumer_secret": "your_secret",
    "passkey": "your_passkey",
    "shortcode": "174379",
    "environment": "sandbox"
}
```

## Do You Need to Restart Your Laptop?

**NO** - You do NOT need to restart your laptop.

**What you need to do:**
1. Close the executable
2. Edit the config files in the correct location
3. Restart the executable

## Quick Reference

| Action | Location |
|--------|----------|
| Development testing | Edit project directory files |
| Executable testing | Edit `~/FreemanSchoolPortal/` files |
| Production distribution | Rebuild executable with new config |
| Fresh config | Delete `~/FreemanSchoolPortal/` directory |

## Troubleshooting

### Changes Not Reflecting
**Problem:** You edited files but executable shows old values
**Solution:** You're editing project files instead of user data directory files

### Can't Find User Data Directory
**Problem:** Don't know where to edit config
**Solution:** Navigate to `C:\Users\<Username>\FreemanSchoolPortal\`

### Want to Reset Everything
**Problem:** Want to start fresh with new config
**Solution:** Delete `C:\Users\<Username>\FreemanSchoolPortal\` and run executable

### Changes Lost After Rebuild
**Problem:** Rebuilt executable but changes are gone
**Solution:** Rebuild copies bundled files, not user data files. Edit project files before rebuilding.

## Summary

**For immediate testing:** Edit files in `C:\Users\<Username>\FreemanSchoolPortal\`

**For production:** Edit project files, then rebuild executable

**No laptop restart required** - just restart the executable.
