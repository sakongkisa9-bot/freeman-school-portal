# Update Server Setup Guide

This guide explains how to set up a remote update server for the Freeman School Portal system.

## Server Structure

Create a web server with the following structure:

```
your-server.com/
└── updates/
    └── freeman_school_portal/
        ├── version.json
        └── freeman_update_1.0.1.zip
```

## version.json Format

The `version.json` file on the server should contain:

```json
{
    "version": "1.0.1",
    "release_date": "2027-06-16",
    "changelog": "Fixed bug in payment processing and added new features",
    "download_url": "https://your-server.com/updates/freeman_school_portal/freeman_update_1.0.1.zip"
}
```

## Update Package Format

The update package (`.zip` file) should contain:
- All updated Python files
- Updated version.json
- Any new assets or configuration files
- **DO NOT** include database files (`.db`) - these should be preserved

## Creating an Update Package

1. Make your changes to the code
2. Update the version number in `version.json`
3. Create a zip file with the updated files:
   ```bash
   # On Windows
   powershell Compress-Archive -Path *.py,version.json,assets -DestinationPath freeman_update_1.0.1.zip
   
   # On Linux/Mac
   zip -r freeman_update_1.0.1.zip *.py version.json assets/
   ```

4. Upload the zip file to your update server
5. Update the `version.json` on the server with the new version info

## Client Configuration

Edit `update_config.json` in the client installation:

```json
{
    "update_url": "https://your-server.com/updates/freeman_school_portal/",
    "auto_check": true,
    "check_interval_hours": 24
}
```

## Update Process

When the user clicks "Check Updates":
1. System fetches `version.json` from the server
2. Compares versions using semantic versioning
3. If newer version exists, shows update dialog
4. User can download and install the update
5. System backs up current files
6. Extracts new files
7. Updates `version.json`
8. Prompts user to restart

## Security Considerations

- Use HTTPS for your update server
- Consider adding authentication tokens
- Sign update packages for verification
- Keep backup of previous versions for rollback

## Testing Updates

Before deploying to production:
1. Test the update package on a clean installation
2. Verify database compatibility
3. Test rollback functionality
4. Ensure all dependencies are included

## Example Server Setup (Flask)

```python
from flask import Flask, send_file, jsonify
import os

app = Flask(__name__)

UPDATE_DIR = "updates/freeman_school_portal"

@app.route('/updates/freeman_school_portal/version.json')
def get_version():
    version_file = os.path.join(UPDATE_DIR, "version.json")
    with open(version_file) as f:
        return jsonify(json.load(f))

@app.route('/updates/freeman_school_portal/<filename>')
def download_update(filename):
    file_path = os.path.join(UPDATE_DIR, filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(ssl_context='adhoc', port=443)
```

## Version Numbering

Use semantic versioning: `MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: New features
- PATCH: Bug fixes

Example: `1.0.0` → `1.0.1` → `1.1.0` → `2.0.0`
