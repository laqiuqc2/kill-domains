# Windows 网站访问控制程序

一个专为 Windows 设计的网站访问控制程序，通过修改系统 hosts 文件将指定域名重定向到本地来屏蔽网站访问。程序完全隐藏在后台运行，通过系统托盘图标管理。

## 功能特性

- ✅ **自动同步域名列表**: 每次启动程序后，从 API 获取最新域名列表并更新到 `domains.txt`
- ✅ **实时屏蔽**: 自动屏蔽 `domains.txt` 中的域名访问
- ✅ **定时检查**: 每 15 秒检查并同步更新屏蔽规则
- ✅ **一键恢复**: 通过系统托盘菜单一键清理所有屏蔽规则，恢复网站正常访问
- ✅ **后台运行**: 创建隐藏窗口，仅在系统托盘显示图标
- ✅ **托盘菜单**: 支持托盘菜单操作（立即同步、恢复访问、退出）

## 系统要求

- Windows 7 或更高版本
- Python 3.7+ (开发环境)
- 管理员权限 (运行时需要，用于修改 hosts 文件)

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 开发环境运行

```bash
python kill_domains.py
```

**注意**: 需要以管理员身份运行，否则无法修改 hosts 文件。

### 编译为 exe 文件

#### 方法一：使用 build.spec 文件（推荐）

1. 安装 PyInstaller:
```bash
pip install pyinstaller
```

2. 编译:
```bash
pyinstaller build.spec
```

3. 编译完成后，exe 文件位于 `dist/DomainKiller.exe`

#### 方法二：使用 build_exe.py 脚本

```bash
python build_exe.py
```

#### 方法三：直接使用 PyInstaller 命令

```bash
pyinstaller --onefile --windowed --name=DomainKiller --add-data="domains.txt;." kill_domains.py
```

### 在 Mac 上为 Windows 编译

由于 PyInstaller 不支持跨平台编译，有以下几种方案：

#### 方案一：使用 GitHub Actions 自动编译（推荐）⭐

这是最简单的方法，无需本地 Windows 环境。

1. 将代码推送到 GitHub
2. GitHub Actions 会自动在 Windows 环境中编译
3. 在 Actions 页面下载编译好的 exe 文件

详细说明请查看 [编译指南.md](编译指南.md)

#### 方案二：使用 Windows 虚拟机

1. 在 Mac 上安装 Windows 虚拟机（Parallels Desktop、VMware Fusion 等）
2. 在虚拟机中安装 Python 和依赖
3. 按照上述编译步骤执行

#### 方案三：使用远程 Windows 服务器

如果有 Windows 服务器或远程桌面，可以在服务器上编译。

详细说明请查看 [编译指南.md](编译指南.md)

## 运行程序

1. **以管理员身份运行** `DomainKiller.exe`
   - 右键点击 exe 文件
   - 选择"以管理员身份运行"

2. 程序启动后会在系统托盘显示图标（红色圆形图标）

3. 右键点击托盘图标可以：
   - **立即同步**: 立即从 API 获取最新域名并更新屏蔽规则
   - **恢复访问**: 移除所有屏蔽规则，恢复网站正常访问
   - **退出**: 退出程序（不会自动恢复屏蔽规则）

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
- 返回格式: JSON，包含 `data.domains` 数组

## 工作原理

1. 程序启动时从 API 获取域名列表并更新 `domains.txt`
2. 读取 `domains.txt` 中的域名
3. 在 Windows hosts 文件中添加规则，将域名指向 `127.0.0.1`
4. 每 15 秒检查一次，同步更新屏蔽规则
5. 所有屏蔽规则都标记在 hosts 文件中，便于一键清理

## 注意事项

⚠️ **重要提示**:

1. **管理员权限**: 修改 hosts 文件需要管理员权限，必须右键"以管理员身份运行"
2. **备份 hosts 文件**: 建议在首次运行前备份原始 hosts 文件
3. **防火墙/杀毒软件**: 某些杀毒软件可能会拦截程序修改 hosts 文件的行为
4. **网络连接**: 需要网络连接才能从 API 获取域名列表

## 故障排除

### 程序无法修改 hosts 文件

- 确保以管理员身份运行
- 检查 hosts 文件是否被其他程序锁定
- 检查杀毒软件是否阻止了修改

### 程序无法从 API 获取域名

- 检查网络连接
- 检查 API 地址是否可访问
- 查看程序日志（如果有控制台窗口）

### 系统托盘图标不显示

- 检查系统托盘区域是否隐藏了图标
- 重启程序
- 检查是否有其他程序占用托盘资源

## 开发说明

### 项目结构

```
kill/
├── kill_domains.py      # 主程序文件
├── domains.txt          # 域名列表文件
├── requirements.txt     # Python 依赖
├── build.spec           # PyInstaller 配置文件
├── build_exe.py         # 编译脚本
├── api说明.md           # API 说明文档
└── README.md            # 本文件
```

### 主要模块

- `DomainKiller`: 主控制类
  - `fetch_domains_from_api()`: 从 API 获取域名
  - `update_domains_file()`: 更新 domains.txt
  - `block_domains()`: 屏蔽域名
  - `restore_hosts()`: 恢复 hosts 文件
  - `sync_and_block()`: 同步并屏蔽

## 许可证

本项目仅供学习和个人使用。

## 更新日志

### v1.0.0
- 初始版本
- 实现基本功能：API 同步、域名屏蔽、系统托盘、定时检查

