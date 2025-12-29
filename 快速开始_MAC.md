# macOS 版本快速开始指南

## 一、开发环境运行

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 运行程序

```bash
python3 kill_domains_mac.py
```

首次运行会提示输入管理员密码（用于修改 `/etc/hosts` 文件）。

## 二、编译为可执行文件

### 方法一：单架构编译（推荐）

适用于只在当前 Mac 架构上运行：

```bash
# 1. 安装 PyInstaller
pip3 install pyinstaller

# 2. 运行编译脚本
./build_mac.sh

# 3. 给可执行文件添加执行权限
chmod +x dist/DomainKiller

# 4. 运行程序
./dist/DomainKiller
```

### 方法二：通用二进制编译（支持 M1 和 Intel）

适用于需要同时支持 M1 ARM 和 Intel Mac：

**在 M1 Mac 上运行（推荐）:**

```bash
# 1. 安装 PyInstaller
pip3 install pyinstaller

# 2. 运行通用二进制编译脚本
./build_mac_universal.sh

# 3. 给可执行文件添加执行权限
chmod +x dist/DomainKiller

# 4. 验证架构（应该显示两种架构）
lipo -info dist/DomainKiller

# 5. 运行程序
./dist/DomainKiller
```

**在 Intel Mac 上运行:**

```bash
# 1. 安装 PyInstaller
pip3 install pyinstaller

# 2. 运行通用二进制编译脚本
./build_mac_universal.sh

# 注意：在 Intel Mac 上只能编译 x86_64 版本
# 如需创建通用二进制，需要：
# - 在 M1 Mac 上编译 ARM64 版本
# - 在 Intel Mac 上编译 x86_64 版本
# - 使用 lipo 合并：lipo -create -output dist/DomainKiller dist_arm64/DomainKiller dist_x86_64/DomainKiller
```

## 三、使用程序

### 1. 启动程序

运行编译后的可执行文件：
```bash
./dist/DomainKiller
```

首次运行会提示输入管理员密码。

### 2. 系统托盘图标

程序启动后会在系统托盘（菜单栏右上角）显示红色圆形图标。

### 3. 主窗口操作

- 右键点击托盘图标 → 选择"显示窗口"
- 或直接点击托盘图标（某些 macOS 版本）

主窗口功能：
- **立即同步**: 立即从 API 获取最新域名并更新屏蔽规则
- **刷新列表**: 刷新显示的域名列表
- **恢复访问**: 输入密码后恢复所有网站访问
- **退出程序**: 输入密码后退出程序
- **开机启动**: 勾选后设置开机自动启动

### 4. 托盘菜单操作

右键点击托盘图标：
- **显示窗口**: 显示主控制窗口
- **立即同步**: 立即同步域名列表
- **恢复访问**: 恢复网站访问（需要密码）
- **退出**: 退出程序（需要密码）

## 四、常见问题

### Q: 编译时提示找不到模块？

A: 确保所有依赖都已安装：
```bash
pip3 install -r requirements.txt
```

### Q: 编译后的程序无法运行？

A: 
1. 检查执行权限：`chmod +x dist/DomainKiller`
2. 检查是否缺少动态库：`otool -L dist/DomainKiller`

### Q: 程序无法修改 hosts 文件？

A: 
1. 确保有管理员权限
2. 首次运行时会提示输入密码
3. 如果仍然失败，尝试手动运行：`sudo chmod 644 /etc/hosts`

### Q: 系统托盘图标不显示？

A: 
1. 检查系统托盘区域是否隐藏了图标
2. macOS 可能需要授予辅助功能权限（系统设置 → 隐私与安全性 → 辅助功能）
3. 重启程序

### Q: 如何创建通用二进制文件？

A: 
- **最简单方法**: 在 M1 Mac 上运行 `./build_mac_universal.sh`，脚本会自动处理两种架构
- **手动方法**: 分别在 M1 和 Intel Mac 上编译，然后使用 `lipo` 合并

## 五、系统要求

- macOS 10.14 (Mojave) 或更高版本
- Python 3.7+ (仅开发环境需要)
- 管理员权限（运行时需要）

## 六、架构支持

- ✅ M1 ARM (Apple Silicon)
- ✅ Intel x86_64 (2015年及以后的 Mac)
- ✅ 通用二进制（使用 `build_mac_universal.sh` 编译）

## 七、更多信息

详细文档请查看 [README_MAC.md](README_MAC.md)

