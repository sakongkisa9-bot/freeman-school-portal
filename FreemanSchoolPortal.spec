# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('templates', 'templates'), ('static', 'static'), ('tesseract', 'tesseract'), ('school_config.json', '.'), ('notification_config.json', '.'), ('update_config.json', '.'), ('version.json', '.'), ('mpesa_config.json', '.'), ('file_loader.py', '.'), ('001_cbc_assessment.sql', '.'), ('cbc_curriculum_import.py', '.')],
    hiddenimports=['customtkinter', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont', 'sqlite3', 'flask', 'werkzeug', 'requests', 'firebase_admin', 'grading_logic', 'license_manager', 'security', 'database', 'teacher_comments', 'cba_logic', 'cbc_engine', 'cba_task_manager', 'cba_results_view', 'cbc_curriculum_import', 'create_exam_dialog', 'marksheet_chooser', 'excel_student_import', 'ui_marksheet_playgroup', 'ui_marksheet_pp1', 'ui_marksheet_pp2', 'ui_marksheet_lower', 'ui_marksheet_primary', 'ui_marksheet_junior', 'ui_summary', 'teachers_linked', 'cbc_levels_view', 'cbc_strands_view', 'kicd_grading', 'ui_marksheet_kicd', 'pdfplumber', 'fpdf'],
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
    name='FreemanSchoolPortal',
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
