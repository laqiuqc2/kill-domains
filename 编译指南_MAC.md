# macOS 编译指南

## 当前状态

由于环境依赖问题（pyobjc-core 需要编译，但当前环境可能缺少某些工具），建议手动执行以下步骤来编译。

## 编译步骤

### 步骤 1: 安装依赖

```bash
# 确保 Python 版本 >= 3.10（推荐）或安装 importlib-metadata
pip3 install importlib-metadata>=4.6

# 安装基础依赖
pip3 install requests>=2.31.0 Pillow>=10.0.0 pyinstaller

# 安装 pystray（可能需要编译，如果失败请查看下面的解决方案）
pip3 install pystray>=0.19.5
```

**如果 pystray 安装失败（pyobjc-core 编译错误）:**

**方案 A: 安装 Xcode 命令行工具（推荐）**
```bash
# 检查是否已安装
xcode-select -p

# 如果未安装，运行：
xcode-select --install

# 安装完成后，再次尝试安装 pystray
pip3 install pystray>=0.19.5
```

**方案 B: 使用预编译的 wheel（如果可用）**
```bash
pip3 install pystray>=0.19.5 --only-binary :all:
```

**方案 C: 跳过系统托盘功能（临时方案）**
如果暂时无法安装 pystray，可以修改代码暂时禁用系统托盘功能。

### 步骤 2: 编译

**方法一：单架构编译（当前 Mac 架构）**
```bash
./build_mac.sh
```

**方法二：通用二进制编译（支持 M1 和 Intel）**
```bash
./build_mac_universal.sh
```

**方法三：手动编译**
```bash
# 清理之前的构建
rm -rf build dist

# 编译
pyinstaller build_mac.spec --clean
```

### 步骤 3: 检查编译结果

编译完成后，检查 `dist/` 目录：

```bash
ls -la dist/
```

应该能看到 `DomainKiller.app` 文件夹。

### 步骤 4: 运行

```bash
# 方法一：双击运行
open dist/DomainKiller.app

# 方法二：命令行运行
./dist/DomainKiller.app/Contents/MacOS/DomainKiller
```

## 常见问题

### Q1: pyobjc-core 编译失败

**错误信息**: `error: Cannot locate a working compiler`

**解决方案**:
1. 确保已安装 Xcode 命令行工具：
   ```bash
   xcode-select --install
   ```
2. 检查编译器：
   ```bash
   which gcc
   which clang
   ```
3. 如果已安装但仍失败，尝试：
   ```bash
   sudo xcode-select --switch /Library/Developer/CommandLineTools
   ```

### Q2: PyInstaller 版本问题

**错误信息**: `PyInstaller requires importlib.metadata`

**解决方案**:
```bash
# Python 3.9 需要安装 importlib-metadata
pip3 install importlib-metadata>=4.6

# 或者升级到 Python 3.10+
```

### Q3: 编译后的 app 无法运行

**检查项**:
1. 检查执行权限：
   ```bash
   chmod +x dist/DomainKiller.app/Contents/MacOS/DomainKiller
   ```
2. 检查架构：
   ```bash
   file dist/DomainKiller.app/Contents/MacOS/DomainKiller
   ```
3. 查看错误日志：
   ```bash
   ./dist/DomainKiller.app/Contents/MacOS/DomainKiller
   ```

## 快速编译命令（一键执行）

如果所有依赖都已安装，可以直接运行：

```bash
# 清理并编译
rm -rf build dist && pyinstaller build_mac.spec --clean

# 检查结果
ls -la dist/DomainKiller.app
```

## 编译后的文件位置

```
dist/
  └── DomainKiller.app/          # macOS 应用程序包
      ├── Contents/
      │   ├── Info.plist         # 应用信息
      │   ├── MacOS/
      │   │   └── DomainKiller   # 实际可执行文件
      │   └── Resources/         # 资源文件
      └── ...
```

## 系统要求

- macOS 10.14 (Mojave) 或更高版本
- Python 3.9+ (推荐 3.10+)
- Xcode 命令行工具（用于编译某些依赖）
- 管理员权限（运行时需要）

## 架构支持

- ✅ M1 ARM (Apple Silicon) - 当前系统
- ✅ Intel x86_64 (2015年及以后的 Mac)
- ✅ 通用二进制（使用 `build_mac_universal.sh`）

