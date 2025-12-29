#!/bin/bash
# 安装 pystray 脚本
# 尝试多种方法安装 pystray

set -e

echo "=========================================="
echo "安装 pystray（系统托盘功能）"
echo "=========================================="
echo ""

# 方法一：设置编译器环境变量后安装
echo "方法一：使用 clang 编译器安装..."
export CC=clang
export CXX=clang++
export ARCHFLAGS="-arch arm64"  # 对于 M1 Mac

if pip3 install pystray>=0.19.5 2>&1 | grep -q "Successfully installed"; then
    echo "✅ pystray 安装成功！"
    exit 0
fi

echo ""
echo "方法一失败，尝试方法二..."

# 方法二：使用预编译的 wheel（如果可用）
echo "方法二：尝试使用预编译的 wheel..."
pip3 install pystray>=0.19.5 --only-binary :all: 2>&1 || echo "预编译版本不可用"

echo ""
echo "方法二失败，尝试方法三..."

# 方法三：安装 Xcode 命令行工具
echo "方法三：检查并安装 Xcode 命令行工具..."
if ! xcode-select -p &>/dev/null; then
    echo "正在安装 Xcode 命令行工具..."
    xcode-select --install
    echo "请等待 Xcode 命令行工具安装完成后，再次运行此脚本"
    exit 1
fi

# 方法四：使用 conda（如果可用）
if command -v conda &> /dev/null; then
    echo "方法四：使用 conda 安装..."
    conda install -c conda-forge pystray -y && exit 0
fi

echo ""
echo "❌ 所有安装方法都失败了"
echo ""
echo "建议："
echo "1. 确保已安装 Xcode 命令行工具: xcode-select --install"
echo "2. 升级 pip: pip3 install --upgrade pip"
echo "3. 使用系统自带的 Python（而不是第三方 Python）"
echo "4. 或者使用不包含系统托盘功能的版本（程序仍可正常运行）"

