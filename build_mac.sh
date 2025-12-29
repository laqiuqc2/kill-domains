#!/bin/bash
# macOS 编译脚本
# 支持 M1 ARM 和 Intel Mac

set -e

echo "开始编译 macOS 版本的 DomainKiller..."

# 检查是否安装了 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "错误: 未安装 PyInstaller"
    echo "请运行: pip install pyinstaller"
    exit 1
fi

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $python_version"

# 检测当前架构
arch=$(uname -m)
echo "当前系统架构: $arch"

# 清理之前的构建
echo "清理之前的构建..."
rm -rf build dist *.spec.bak

# 编译
echo "开始编译..."
if [ "$arch" = "arm64" ]; then
    echo "检测到 ARM64 (M1) 架构，编译 ARM64 版本..."
    pyinstaller build_mac.spec --clean
    echo "编译完成！可执行文件位于: dist/DomainKiller"
    echo "注意: 此版本仅支持 ARM64 (M1) Mac"
    echo "如需支持 Intel Mac，请使用 build_mac_universal.sh 脚本"
elif [ "$arch" = "x86_64" ]; then
    echo "检测到 x86_64 (Intel) 架构，编译 x86_64 版本..."
    pyinstaller build_mac.spec --clean
    echo "编译完成！可执行文件位于: dist/DomainKiller"
    echo "注意: 此版本仅支持 x86_64 (Intel) Mac"
    echo "如需支持 M1 Mac，请使用 build_mac_universal.sh 脚本"
else
    echo "未知架构: $arch"
    echo "使用默认配置编译..."
    pyinstaller build_mac.spec --clean
    echo "编译完成！可执行文件位于: dist/DomainKiller"
fi

echo ""
echo "编译完成！"
echo "可执行文件位置: $(pwd)/dist/DomainKiller"
echo ""
echo "使用方法:"
echo "1. 给可执行文件添加执行权限: chmod +x dist/DomainKiller"
echo "2. 运行程序: ./dist/DomainKiller"
echo "3. 首次运行需要输入管理员密码（用于修改 /etc/hosts 文件）"

