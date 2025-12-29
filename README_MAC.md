# macOS 网站访问控制程序

一个专为 macOS 设计的网站访问控制程序，通过修改系统 hosts 文件将指定域名重定向到本地来屏蔽网站访问。程序完全隐藏在后台运行，通过系统托盘图标管理。

支持 **M1 ARM** 和 **Intel Mac**（2015年及以后）。

## 功能特性

- ✅ **自动同步域名列表**: 每次启动程序后，从 API 获取最新域名列表并更新到 `domains.txt`
- ✅ **实时屏蔽**: 自动屏蔽 `domains.txt` 中的域名访问
- ✅ **定时检查**: 每 60 秒检查并同步更新屏蔽规则
- ✅ **一键恢复**: 通过系统托盘菜单一键清理所有屏蔽规则，恢复网站正常访问（需要密码验证）
- ✅ **后台运行**: 创建隐藏窗口，仅在系统托盘显示图标
- ✅ **托盘菜单**: 支持托盘菜单操作（立即同步、恢复访问、退出）
- ✅ **开机启动**: 支持设置开机自动启动
- ✅ **通用二进制**: 支持 M1 ARM 和 Intel Mac

## 系统要求

- macOS 10.14 (Mojave) 或更高版本
- Python 3.7+ (开发环境)
- 管理员权限 (运行时需要，用于修改 hosts 文件)

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 开发环境运行

```bash
python3 kill_domains_mac.py
```

**注意**: 首次运行需要输入管理员密码（用于修改 `/etc/hosts` 文件）。

### 编译为可执行文件

#### 方法一：单架构编译（推荐，简单快速）

1. 安装 PyInstaller:
```bash
pip install pyinstaller
```

2. 运行编译脚本:
```bash
./build_mac.sh
```

3. 编译完成后，可执行文件位于 `dist/DomainKiller`

#### 方法二：通用二进制编译（支持 M1 和 Intel）

如果需要创建一个同时支持 M1 ARM 和 Intel Mac 的通用二进制文件：

**在 M1 Mac 上运行（推荐）:**
```bash
./build_mac_universal.sh
```

此脚本会：
- 在当前 M1 Mac 上编译 ARM64 版本
- 使用 Rosetta 2 编译 x86_64 版本
- 自动合并为通用二进制文件

**在 Intel Mac 上运行:**
```bash
./build_mac_universal.sh
```

然后需要：
1. 在 M1 Mac 上编译 ARM64 版本
2. 使用 `lipo` 命令合并两个版本

#### 方法三：手动使用 PyInstaller

```bash
pyinstaller build_mac.spec
```

### 运行程序

1. **给可执行文件添加执行权限**:
```bash
chmod +x dist/DomainKiller
```

2. **运行程序**:
```bash
./dist/DomainKiller
```

3. **首次运行需要输入管理员密码**（用于修改 `/etc/hosts` 文件）

4. 程序启动后会在系统托盘显示图标（红色圆形图标）

5. 右键点击托盘图标可以：
   - **显示窗口**: 显示主控制窗口
   - **立即同步**: 立即从 API 获取最新域名并更新屏蔽规则
   - **恢复访问**: 移除所有屏蔽规则，恢复网站正常访问（需要密码验证）
   - **退出**: 退出程序（需要密码验证）

## 配置文件

### domains.txt

程序会自动从 API 获取域名列表并更新到此文件。文件格式为每行一个域名：

```
www.baidu.com
www.163.com
www.qq.com
```

## API 说明

程序从以下 API 获取域名列表：
- URL: `https://app.walkingcode.com/API/kill-domains.php`
- 返回格式: JSON，包含 `data.domains` 数组和 `password` 字段

## 工作原理

1. 程序启动时从 API 获取域名列表并更新 `domains.txt`
2. 读取 `domains.txt` 中的域名
3. 在 macOS hosts 文件 (`/etc/hosts`) 中添加规则，将域名指向 `127.0.0.1`
4. 每 60 秒检查一次，同步更新屏蔽规则
5. 所有屏蔽规则都标记在 hosts 文件中，便于一键清理

## 开机启动

程序支持设置开机自动启动，使用 macOS 的 LaunchAgent 机制：

1. 打开主窗口
2. 勾选"开机启动"复选框
3. 程序会自动创建 LaunchAgent plist 文件

取消开机启动：
1. 打开主窗口
2. 取消勾选"开机启动"复选框

## 注意事项

⚠️ **重要提示**:

1. **管理员权限**: 修改 hosts 文件需要管理员权限，首次运行时会提示输入密码
2. **备份 hosts 文件**: 建议在首次运行前备份原始 hosts 文件
   ```bash
   sudo cp /etc/hosts /etc/hosts.backup
   ```
3. **防火墙/安全软件**: 某些安全软件可能会拦截程序修改 hosts 文件的行为
4. **网络连接**: 需要网络连接才能从 API 获取域名列表
5. **通用二进制**: 如果需要在 M1 和 Intel Mac 上都能运行，请使用 `build_mac_universal.sh` 编译

## 故障排除

### 程序无法修改 hosts 文件

- 确保有管理员权限
- 检查 hosts 文件是否被其他程序锁定
- 检查安全软件是否阻止了修改
- 尝试手动运行: `sudo chmod 644 /etc/hosts`

### 程序无法从 API 获取域名

- 检查网络连接
- 检查 API 地址是否可访问
- 查看程序日志（如果有控制台窗口）

### 系统托盘图标不显示

- 检查系统托盘区域是否隐藏了图标
- 重启程序
- 检查是否有其他程序占用托盘资源
- macOS 可能需要授予辅助功能权限

### 编译问题

**问题**: 编译时提示找不到模块
- 解决: 确保所有依赖都已安装: `pip install -r requirements.txt`

**问题**: 编译后的程序无法运行
- 解决: 检查是否有执行权限: `chmod +x dist/DomainKiller`
- 解决: 检查是否缺少动态库，使用 `otool -L dist/DomainKiller` 查看

**问题**: 通用二进制编译失败
- 解决: 确保在 M1 Mac 上运行 `build_mac_universal.sh`，它会自动处理两种架构
- 解决: 如果 Rosetta 2 不可用，需要分别在两种架构的 Mac 上编译后手动合并

## 开发说明

### 项目结构

```
kill/
├── kill_domains_mac.py      # macOS 主程序文件
├── domains.txt               # 域名列表文件
├── requirements.txt          # Python 依赖
├── build_mac.spec            # PyInstaller 配置文件（单架构）
├── build_mac_universal.spec  # PyInstaller 配置文件（通用二进制）
├── build_mac.sh              # 编译脚本（单架构）
├── build_mac_universal.sh    # 编译脚本（通用二进制）
├── api说明.md                # API 说明文档
└── README_MAC.md             # 本文件
```

### 主要模块

- `DomainKiller`: 主控制类
  - `fetch_domains_from_api()`: 从 API 获取域名
  - `update_domains_file()`: 更新 domains.txt
  - `block_domains()`: 屏蔽域名（使用 sudo）
  - `restore_hosts()`: 恢复 hosts 文件（使用 sudo）
  - `sync_and_block()`: 同步并屏蔽
  - `enable_startup()`: 启用开机启动（LaunchAgent）
  - `disable_startup()`: 禁用开机启动

### macOS 特定实现

1. **hosts 文件操作**: 使用 `sudo` 命令通过 subprocess 调用
2. **开机启动**: 使用 LaunchAgent (plist 文件)
3. **系统托盘**: 使用 pystray（跨平台）
4. **权限管理**: 通过 sudo 提示用户输入密码

## 与 Windows 版本的差异

1. **hosts 文件路径**: `/etc/hosts` (macOS) vs `C:\Windows\System32\drivers\etc\hosts` (Windows)
2. **权限管理**: sudo (macOS) vs 管理员权限 (Windows)
3. **开机启动**: LaunchAgent (macOS) vs 注册表 (Windows)
4. **窗口隐藏**: macOS 不需要隐藏控制台窗口

## 许可证

本项目仅供学习和个人使用。

## 更新日志

### v1.0.0 (macOS)
- 初始 macOS 版本
- 实现基本功能：API 同步、域名屏蔽、系统托盘、定时检查
- 支持 M1 ARM 和 Intel Mac
- 支持开机启动（LaunchAgent）

