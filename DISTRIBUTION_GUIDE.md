# Freeman School Portal - Distribution Guide

## What Files to Distribute

### Single Executable Distribution (Recommended)

**For most users, you only need to distribute the single executable file:**

```
FreemanSchoolPortal_Secure.exe
```

**Why this works:**
- The executable is self-contained with all necessary files bundled inside
- All assets (images, templates, static files) are embedded
- All configuration files are included
- The application creates its own user data directory on first run

### When to Use Single Executable

✅ **Use single executable when:**
- Distributing to end users/schools
- Simple installation process desired
- No custom configuration needed before first run
- Users will run the application directly

### Additional Files (Optional)

You may optionally include these files for advanced users:

```
README.txt - Installation and usage instructions
LICENSE.txt - License terms and conditions
CHANGELOG.txt - Version history and updates
```

## Installation Process

### For End Users

1. **Download** the `FreemanSchoolPortal_Secure.exe` file
2. **Run** the executable (double-click)
3. **First Run Setup:**
   - Application will create `~/FreemanSchoolPortal/` directory
   - License activation will be required
   - Terms of Use agreement will be shown
   - Initial setup wizard will guide configuration

### No Additional Files Required

The executable automatically handles:
- ✅ Database creation and management
- ✅ Configuration file generation
- ✅ Asset file extraction
- ✅ Template file loading
- ✅ User data directory creation
- ✅ Update mechanism

## User Data Directory

The application automatically creates:

```
C:\Users\<Username>\FreemanSchoolPortal\
├── freeman_data.db (database file)
├── school_config.json (school configuration)
├── notification_config.json (notification settings)
├── update_config.json (update server settings)
├── archives/ (exam archives and backups)
└── logs/ (application logs)
```

**This directory is created automatically on first run - no manual setup required.**

## Configuration Files

### Pre-configuration (Optional)

If you want to pre-configure the application before distribution, you can include:

```
school_config.json - Pre-configured school settings
notification_config.json - Pre-configured notification settings
update_config.json - Pre-configured update server
```

**How to use pre-configuration:**
1. Place these files in the same directory as the executable
2. The application will detect and use them on first run
3. Users can still modify settings after installation

### Default Configuration

If no configuration files are present, the application will:
- Create default configuration files
- Run the setup wizard
- Prompt for necessary information

## System Requirements

### Minimum Requirements
- **OS:** Windows 10 or later (64-bit)
- **RAM:** 4 GB minimum, 8 GB recommended
- **Disk Space:** 500 MB for application + 100 MB for data
- **Display:** 1024x768 minimum resolution

### Recommended Requirements
- **OS:** Windows 10 or later (64-bit)
- **RAM:** 8 GB or more
- **Disk Space:** 1 GB for application + 500 MB for data
- **Display:** 1920x1080 or higher

## Distribution Methods

### Direct Download
- Upload `FreemanSchoolPortal_Secure.exe` to your website/server
- Provide download link to users
- No installation wizard needed

### USB Drive Distribution
- Copy executable to USB drive
- Users can run directly from USB or copy to computer
- Portable and convenient

### Email Distribution
- Send executable as email attachment (if size permits)
- Use cloud storage link for larger files
- Include installation instructions

## Security Considerations

### Executable Security
- ✅ Code obfuscation with PyArmor
- ✅ License validation system
- ✅ Encrypted sensitive operations
- ✅ No source code exposure

### Distribution Security
- ✅ Single file reduces tampering risk
- ✅ Built-in license verification
- ✅ Automatic update mechanism
- ✅ Secure configuration storage

## Troubleshooting Distribution

### Common Issues

**Issue:** Antivirus flags the executable
**Solution:** The executable is obfuscated which may trigger false positives. Add to antivirus exceptions.

**Issue:** Windows Defender SmartScreen warning
**Solution:** This is normal for new executables. Users can click "More info" then "Run anyway".

**Issue:** Missing files error
**Solution:** Ensure only the executable is distributed. All dependencies are bundled inside.

**Issue:** Configuration not loading
**Solution:** Place config files in same directory as executable before first run.

## Version Updates

### Update Mechanism
The application includes automatic update functionality:
- Checks for updates on startup
- Downloads and applies updates automatically
- Preserves user data during updates
- Requires no user intervention

### Manual Updates
If automatic updates fail:
1. Download new executable
2. Replace old executable
3. User data is preserved automatically

## Support Files

### Recommended Support Files to Include

```
README.txt
----------
Freeman School Portal - Installation Guide

1. Download FreemanSchoolPortal_Secure.exe
2. Run the executable
3. Follow the setup wizard
4. Activate your license
5. Start using the system

For support: support@freemantech.com
Website: www.freemantech.com

LICENSE.txt
----------
[Your license terms and conditions]

SUPPORT.txt
----------
Technical Support Information
- Email: support@freemantech.com
- Phone: [Your phone number]
- Hours: [Your support hours]
```

## Summary

**For distribution, you only need:**
- ✅ `FreemanSchoolPortal_Secure.exe` (required)

**Optionally include:**
- 📄 README.txt (recommended)
- 📄 LICENSE.txt (recommended)  
- 📄 SUPPORT.txt (optional)
- 📄 Pre-configured JSON files (optional)

**No other files needed - everything is self-contained!**
