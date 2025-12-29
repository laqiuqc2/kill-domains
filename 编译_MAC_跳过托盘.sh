#!/bin/bash
# macOS 编译脚本（跳过系统托盘依赖）
# 如果 pystray 安装失败，使用此脚本编译不包含系统托盘功能的版本

set -e

echo "=========================================="
echo "macOS DomainKiller 编译脚本（跳过系统托盘）"
echo "=========================================="
echo ""

# 检测架构
arch=$(uname -m)
echo "检测到系统架构: $arch"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

python_version=$(python3 --version)
echo "Python 版本: $python_version"
echo ""

# 安装基础依赖（不包含 pystray）
echo "步骤 1/3: 安装基础依赖..."
echo "----------------------------------------"

# 检查 Python 版本，如果是 3.9 需要安装 importlib-metadata
python_version_num=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
if [ "$(printf '%s\n' "3.9" "$python_version_num" | sort -V | head -n1)" = "3.9" ]; then
    echo "检测到 Python 3.9，安装 importlib-metadata..."
    pip3 install importlib-metadata>=4.6 || echo "警告: importlib-metadata 安装失败"
fi

# 安装基础依赖
pip3 install requests>=2.31.0 Pillow>=10.0.0 pyinstaller altgraph macholib packaging pyinstaller-hooks-contrib
echo "✅ 基础依赖安装完成"
echo ""

# 检查依赖是否安装成功
echo "步骤 2/3: 检查依赖..."
echo "----------------------------------------"
if ! command -v pyinstaller &> /dev/null; then
    echo "错误: PyInstaller 安装失败"
    exit 1
fi
echo "✅ PyInstaller 已安装"
echo ""

# 清理之前的构建
echo "步骤 3/3: 开始编译..."
echo "----------------------------------------"
rm -rf build dist *.spec.bak

# 编译
if [ "$arch" = "arm64" ]; then
    echo "编译 ARM64 版本..."
    pyinstaller build_mac.spec --clean
elif [ "$arch" = "x86_64" ]; then
    echo "编译 x86_64 版本..."
    pyinstaller build_mac.spec --clean
else
    echo "编译默认版本..."
    pyinstaller build_mac.spec --clean
fi

echo ""
echo "=========================================="
echo "✅ 编译完成！"
echo "=========================================="
echo ""
echo "编译好的 app 位置:"
echo "  $(pwd)/dist/DomainKiller.app"
echo ""
echo "注意: 此版本不包含系统托盘功能（pystray 未安装）"
echo "程序将通过主窗口运行，关闭窗口将退出程序"
echo ""
echo "使用方法:"
echo "  1. 双击运行: open dist/DomainKiller.app"
echo "  2. 或命令行运行: ./dist/DomainKiller.app/Contents/MacOS/DomainKiller"
echo ""
echo "首次运行需要输入管理员密码（用于修改 /etc/hosts 文件）"
echo ""

