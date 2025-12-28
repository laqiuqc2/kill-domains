#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
编译脚本 - 用于将 Python 程序编译为 Windows exe
使用方法: python build_exe.py
"""

import subprocess
import sys
import os

def build_exe():
    """使用 PyInstaller 编译 exe"""
    print("开始编译 Windows exe...")
    
    # PyInstaller 命令
    cmd = [
        "pyinstaller",
        "--onefile",                    # 打包成单个 exe 文件
        "--windowed",                   # 隐藏控制台窗口
        "--name=DomainKiller",          # 输出文件名
        "--icon=NONE",                  # 可以指定图标文件路径
        "--add-data=domains.txt;.",     # 包含 domains.txt 文件
        "--hidden-import=pystray",      # 确保包含 pystray
        "--hidden-import=PIL",          # 确保包含 PIL
        "--hidden-import=win32gui",     # 确保包含 win32gui
        "--hidden-import=win32con",     # 确保包含 win32con
        "--hidden-import=win32process", # 确保包含 win32process
        "--hidden-import=win32api",     # 确保包含 win32api
        "kill_domains.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n编译完成！")
        print("exe 文件位置: dist/DomainKiller.exe")
        print("\n注意: 在 Windows 上运行时需要以管理员身份运行")
    except subprocess.CalledProcessError as e:
        print(f"编译失败: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("错误: 未找到 PyInstaller")
        print("请先安装: pip install pyinstaller")
        sys.exit(1)


if __name__ == "__main__":
    build_exe()

