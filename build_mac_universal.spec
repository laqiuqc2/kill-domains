# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件 - macOS 通用二进制版本
支持 M1 ARM 和 Intel Mac（需要分别编译后合并）
使用方法: 
1. 在 Intel Mac 上: pyinstaller build_mac_universal.spec --target-arch x86_64
2. 在 M1 Mac 上: pyinstaller build_mac_universal.spec --target-arch arm64
3. 使用 lipo 合并: lipo -create -output dist/DomainKiller dist_x86_64/DomainKiller dist_arm64/DomainKiller

或者使用 build_mac_universal.sh 脚本自动完成
"""

block_cipher = None

a = Analysis(
    ['kill_domains_mac.py'],
    pathex=[],
    binaries=[],
    datas=[('domains.txt', '.')],  # 包含 domains.txt 文件
    hiddenimports=[
        'pystray',
        'PIL',
        'PIL._tkinter_finder',
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
    upx=False,  # macOS 上 UPX 可能有问题，禁用
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # 通过命令行参数指定
    codesign_identity=None,  # 如果需要代码签名，设置证书名称
    entitlements_file=None,  # 如果需要，指定 entitlements 文件路径
    icon=None,  # 可以指定图标文件路径，如: icon='icon.icns'
)

# 创建 .app 包（macOS 应用程序包）
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
        'NSHumanReadableCopyright': 'Copyright © 2025',
    },
)

