#!/bin/bash
# macOS 简化版编译脚本
# 使用更稳定的简化版本

set -e

echo "=========================================="
echo "macOS DomainKiller 简化版编译"
echo "=========================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

python_version=$(python3 --version)
echo "Python 版本: $python_version"
echo ""

# 检查 Python 版本
python_version_num=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
if [ "$(printf '%s\n' "3.9" "$python_version_num" | sort -V | head -n1)" = "3.9" ]; then
    echo "安装 importlib-metadata..."
    pip3 install importlib-metadata>=4.6 2>&1 | grep -v "WARNING" || true
fi

# 安装基础依赖
echo "安装基础依赖..."
pip3 install requests>=2.31.0 pyinstaller 2>&1 | grep -v "WARNING" || true

# 检查 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "错误: PyInstaller 未安装"
    exit 1
fi

echo "✅ 依赖检查完成"
echo ""

# 清理并编译
echo "开始编译简化版..."
rm -rf build dist *.spec.bak

pyinstaller build_mac_simple.spec --clean

echo ""
echo "=========================================="
echo "✅ 编译完成！"
echo "=========================================="
echo ""
echo "编译好的 app 位置:"
echo "  $(pwd)/dist/DomainKiller.app"
echo ""
echo "使用方法:"
echo "  open dist/DomainKiller.app"
echo ""

