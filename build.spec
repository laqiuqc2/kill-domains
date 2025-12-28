# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件
使用方法: pyinstaller build.spec
"""

block_cipher = None

a = Analysis(
    ['kill_domains.py'],
    pathex=[],
    binaries=[],
    datas=[('domains.txt', '.')],  # 包含 domains.txt 文件
    hiddenimports=[
        'pystray',
        'PIL',
        'win32gui',
        'win32con',
        'win32process',
        'win32api',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DomainKiller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以指定图标文件路径，如: icon='icon.ico'
)

