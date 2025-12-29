#!/bin/bash
# macOS 通用二进制编译脚本
# 创建支持 M1 ARM 和 Intel Mac 的通用二进制文件
# 注意: 此脚本需要在两种架构的 Mac 上分别运行，然后合并

set -e

echo "开始编译 macOS 通用二进制版本的 DomainKiller..."
echo "此脚本将创建支持 M1 ARM 和 Intel Mac 的通用二进制文件"
echo ""

# 检查是否安装了 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "错误: 未安装 PyInstaller"
    echo "请运行: pip install pyinstaller"
    exit 1
fi

# 检测当前架构
arch=$(uname -m)
echo "当前系统架构: $arch"

# 方法一: 如果当前 Mac 支持 Rosetta 2，可以尝试交叉编译
# 方法二: 分别在两种架构的 Mac 上编译，然后合并

if [ "$arch" = "arm64" ]; then
    echo ""
    echo "=== 方案一: 在当前 M1 Mac 上编译 ARM64 版本 ==="
    echo "编译 ARM64 版本..."
    rm -rf build_arm64 dist_arm64
    pyinstaller build_mac.spec --clean --distpath dist_arm64 --workpath build_arm64
    echo "ARM64 版本编译完成"
    
    echo ""
    echo "=== 方案二: 使用 Rosetta 2 编译 x86_64 版本 ==="
    echo "尝试使用 arch -x86_64 编译 x86_64 版本..."
    if arch -x86_64 /usr/bin/true 2>/dev/null; then
        rm -rf build_x86_64 dist_x86_64
        arch -x86_64 pyinstaller build_mac.spec --clean --distpath dist_x86_64 --workpath build_x86_64
        echo "x86_64 版本编译完成"
        
        # 检查是否安装了 lipo
        if command -v lipo &> /dev/null; then
            echo ""
            echo "=== 合并两个架构的二进制文件 ==="
            rm -rf dist
            mkdir -p dist
            lipo -create -output dist/DomainKiller dist_arm64/DomainKiller dist_x86_64/DomainKiller
            
            # 复制其他文件
            if [ -d dist_arm64 ]; then
                cp -r dist_arm64/* dist/ 2>/dev/null || true
            fi
            
            echo ""
            echo "✅ 通用二进制文件创建成功！"
            echo "文件位置: $(pwd)/dist/DomainKiller"
            echo ""
            echo "验证架构:"
            file dist/DomainKiller
            lipo -info dist/DomainKiller
        else
            echo "警告: 未找到 lipo 命令，无法合并二进制文件"
            echo "ARM64 版本位于: dist_arm64/DomainKiller"
            echo "x86_64 版本位于: dist_x86_64/DomainKiller"
        fi
    else
        echo "错误: 当前系统不支持 Rosetta 2，无法编译 x86_64 版本"
        echo "ARM64 版本已编译完成，位于: dist_arm64/DomainKiller"
        echo ""
        echo "如需创建通用二进制，请："
        echo "1. 在 Intel Mac 上运行此脚本编译 x86_64 版本"
        echo "2. 使用 lipo 合并两个版本:"
        echo "   lipo -create -output dist/DomainKiller dist_arm64/DomainKiller dist_x86_64/DomainKiller"
    fi
    
elif [ "$arch" = "x86_64" ]; then
    echo ""
    echo "=== 在当前 Intel Mac 上编译 x86_64 版本 ==="
    echo "编译 x86_64 版本..."
    rm -rf build_x86_64 dist_x86_64
    pyinstaller build_mac.spec --clean --distpath dist_x86_64 --workpath build_x86_64
    echo "x86_64 版本编译完成，位于: dist_x86_64/DomainKiller"
    
    echo ""
    echo "注意: 在 Intel Mac 上无法直接编译 ARM64 版本"
    echo "如需创建通用二进制，请："
    echo "1. 在 M1 Mac 上运行此脚本编译 ARM64 版本"
    echo "2. 将两个版本合并:"
    echo "   lipo -create -output dist/DomainKiller dist_arm64/DomainKiller dist_x86_64/DomainKiller"
else
    echo "未知架构: $arch"
    echo "使用默认配置编译..."
    pyinstaller build_mac.spec --clean
    echo "编译完成！可执行文件位于: dist/DomainKiller"
fi

echo ""
echo "编译完成！"
echo ""
echo "使用方法:"
echo "1. 给可执行文件添加执行权限: chmod +x dist/DomainKiller"
echo "2. 运行程序: ./dist/DomainKiller"
echo "3. 首次运行需要输入管理员密码（用于修改 /etc/hosts 文件）"

