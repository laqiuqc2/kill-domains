#!/bin/bash
# macOS 一键编译脚本
# 自动安装依赖并编译

set -e

echo "=========================================="
echo "macOS DomainKiller 一键编译脚本"
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

# 安装依赖
echo "步骤 1/3: 安装依赖..."
echo "----------------------------------------"

# 检查 Python 版本，如果是 3.9 需要安装 importlib-metadata
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
if [ "$(printf '%s\n' "3.9" "$python_version" | sort -V | head -n1)" = "3.9" ]; then
    echo "检测到 Python 3.9，需要安装 importlib-metadata..."
    pip3 install importlib-metadata>=4.6 || echo "警告: importlib-metadata 安装失败，请手动安装: pip3 install importlib-metadata>=4.6"
fi

# 先安装基础依赖（不包含 pystray）
echo "安装基础依赖..."
pip3 install requests>=2.31.0 Pillow>=10.0.0 pyinstaller altgraph macholib packaging pyinstaller-hooks-contrib || {
    echo "警告: 部分依赖安装失败，继续尝试..."
}

# 尝试安装 pystray（如果失败，程序仍可编译，但系统托盘功能不可用）
echo "尝试安装 pystray（系统托盘功能）..."
if pip3 install pystray>=0.19.5 2>&1 | grep -q "error\|ERROR\|Failed"; then
    echo "⚠️  警告: pystray 安装失败（系统托盘功能将不可用）"
    echo "   这不会影响其他功能，程序仍可正常编译和运行"
    echo "   如果需要系统托盘功能，请先解决编译器问题："
    echo "   1. 运行: xcode-select --install"
    echo "   2. 或设置: export CC=gcc"
    echo ""
else
    echo "✅ pystray 安装成功"
fi

echo ""

# 检查依赖是否安装成功
echo "步骤 2/3: 检查依赖..."
echo "----------------------------------------"
if ! command -v pyinstaller &> /dev/null; then
    echo "错误: PyInstaller 安装失败"
    echo "尝试使用: pip3 install --user pyinstaller"
    exit 1
fi
echo "✅ 依赖安装完成"
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
echo "使用方法:"
echo "  1. 双击运行: open dist/DomainKiller.app"
echo "  2. 或命令行运行: ./dist/DomainKiller.app/Contents/MacOS/DomainKiller"
echo ""
echo "首次运行需要输入管理员密码（用于修改 /etc/hosts 文件）"
echo ""

