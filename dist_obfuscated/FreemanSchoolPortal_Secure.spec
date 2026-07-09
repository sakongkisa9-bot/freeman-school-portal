# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('templates', 'templates'), ('static', 'static'), ('school_config.json', '.'), ('notification_config.json', '.'), ('update_config.json', '.'), ('version.json', '.'), ('mpesa_config.json', '.'), ('tesseract', 'tesseract')],
    hiddenimports=['customtkinter', 'PIL', 'sqlite3', 'flask', 'werkzeug', 'requests', 'firebase_admin', 'grading_logic', 'license_manager', 'security', 'database', 'pytesseract', 'cv2', 'ocr_student_dialog', 'ocr_service', 'cloud_service', 'cloud_portal_v2', 'notification_service', 'fcm_service', 'mpesa_service', 'update_manager', 'newsletter', 'network_manager', 'hotspot_server', 'teachers_linked', 'reportforms', 'wizard', 'splash', 'ui_marksheet_playgroup', 'ui_marksheet_pp1', 'ui_marksheet_pp2', 'ui_marksheet_lower', 'ui_marksheet_primary', 'ui_marksheet_junior', 'ui_summary'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FreemanSchoolPortal_Secure',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['freeman_icon.ico'],
)
