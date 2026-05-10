# -*- mode: python ; coding: utf-8 -*-
"""
CodeMate — PyInstaller Spec File
Single-file EXE build with all dependencies bundled.
Model is NOT bundled — downloaded on first run (~3GB).
"""
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# ── Collect hidden imports and data for complex packages ─────
datas = []
binaries = []
hiddenimports = [
    'pynvml', 'psutil', 'pyperclip', 'wikipedia', 'platformdirs',
    'peft', 'transformers', 'accelerate', 'torch', 'sentencepiece',
    'protobuf', 'google.genai', 'google.genai.types', 'howdoi',
    'bitsandbytes',
    'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
    'PySide6.QtSvg', 'PySide6.QtNetwork',
]

for pkg in ['transformers', 'peft', 'accelerate', 'tokenizers',
            'sentencepiece', 'google.genai']:
    try:
        tmp = collect_all(pkg)
        datas += tmp[0]
        binaries += tmp[1]
        hiddenimports += tmp[2]
    except Exception:
        pass

# ── Analysis ─────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas + [
        ('assets', 'assets'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'notebook', 'jupyter', 'IPython',
        'tkinter', 'test', 'xmlrpc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Single-file EXE (--onefile mode) ─────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CodeMate',
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
    icon='assets/icon.png',
)
