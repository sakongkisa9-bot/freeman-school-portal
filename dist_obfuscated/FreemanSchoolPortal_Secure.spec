# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['C:/Users/sakon/Documents/FreemanTech_Project (2)/FreemanTech_Project/dist_obfuscated'],
    binaries=[],
    datas=[('assets', 'assets'), ('templates', 'templates'), ('static', 'static'), ('school_config.json', '.'), ('notification_config.json', '.'), ('update_config.json', '.'), ('version.json', '.'), ('mpesa_config.json', '.'), ('tesseract', 'tesseract'), ('file_loader.py', '.'), ('marksheet_chooser.py', '.'), ('create_exam_dialog.py', '.'), ('ui_marksheet_kicd.py', '.'), ('cbc_engine.py', '.'), ('cbc_levels_view.py', '.'), ('cbc_strands_view.py', '.'), ('kicd_grading.py', '.'), ('excel_student_import.py', '.')],
    hiddenimports=['customtkinter', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont', 'sqlite3', 'flask', 'werkzeug', 'requests', 'firebase_admin', 'grading_logic', 'license_manager', 'security', 'database', 'pytesseract', 'cv2', 'ocr_student_dialog', 'ocr_service', 'cloud_service', 'cloud_portal_v2', 'notification_service', 'fcm_service', 'mpesa_service', 'mpesa_callback_server', 'update_manager', 'newsletter', 'network_manager', 'hotspot_server', 'teachers_linked', 'reportforms', 'teacher_comments', 'wizard', 'splash', 'file_loader', 'marksheet_chooser', 'create_exam_dialog', 'ui_marksheet_kicd', 'cbc_engine', 'cbc_levels_view', 'cbc_strands_view', 'kicd_grading', 'excel_student_import', 'ui_marksheet_playgroup', 'ui_marksheet_pp1', 'ui_marksheet_pp2', 'ui_marksheet_lower', 'ui_marksheet_primary', 'ui_marksheet_junior', 'ui_summary', 'cba_logic', 'cba_task_manager', 'cba_results_view', 'fpdf'],
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
