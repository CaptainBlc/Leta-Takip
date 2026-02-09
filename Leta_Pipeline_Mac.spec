# -*- mode: python ; coding: utf-8 -*-
# macOS: onedir .app bundle (DMG/PKG için gerekli)
# Windows için Leta_Pipeline_Final.spec (onefile) kullanın.

block_cipher = None

a = Analysis(
    ['script/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('script/assets/KULLANIM_KILAVUZU.txt', 'assets'),
    ],
    hiddenimports=[
        'ttkbootstrap',
        'ttkbootstrap.constants',
        'ttkbootstrap.themes',
        'ttkbootstrap.style',
        'ttkbootstrap.widgets',
        'ttkbootstrap.dialogs',
        'ttkbootstrap.tooltip',
        'ttkbootstrap.scrolled',
        'pandas',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'openpyxl',
        'tkcalendar',
        'reportlab',
        'reportlab.lib.pagesizes',
        'reportlab.pdfbase.pdfmetrics',
        'reportlab.pdfbase.ttfonts',
        'sqlite3',
        'datetime',
        'hashlib',
        'json',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'tensorflow', 'scipy', 'sklearn', 'matplotlib',
        'cv2', 'transformers', 'spacy', 'cryptography', 'grpc',
        'h5py', 'lxml', 'sympy', 'jinja2', 'pytest',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Leta_Pipeline_v1_3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Leta_Pipeline_v1_3',
)

# macOS .app bundle (DMG/PKG için); Windows'ta bu spec kullanılmaz

app = BUNDLE(
    coll,
    name='Leta_Pipeline_v1_3.app',
    icon=None,
    bundle_identifier='com.leta.takip',
    info_plist={
        'CFBundleName': 'Leta Takip',
        'CFBundleDisplayName': 'Leta Takip',
        'CFBundleVersion': '1.3',
        'CFBundleShortVersionString': '1.3',
        'NSHighResolutionCapable': True,
        'NSAppleEventsUsageDescription': 'Leta Takip uygulaması',
    },
)
