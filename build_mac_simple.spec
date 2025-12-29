# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件 - macOS 简化版
使用简化稳定版本
"""

block_cipher = None

a = Analysis(
    ['kill_domains_mac_simple.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('domains.txt', '.'),  # 将 domains.txt 打包到应用目录
    ],
    hiddenimports=[
        'tkinter',
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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

app = BUNDLE(
    exe,
    name='DomainKiller.app',
    icon=None,
    bundle_identifier='com.domainkiller.app',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleName': 'DomainKiller',
        'CFBundleDisplayName': '网站访问控制',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
    },
)

