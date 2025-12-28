#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows 网站访问控制程序
通过修改 hosts 文件屏蔽指定域名
"""

import os
import sys
import json
import time
import threading
import requests
from pathlib import Path
import pystray
from PIL import Image, ImageDraw

# Windows 相关导入（仅在 Windows 上可用）
if sys.platform == 'win32':
    try:
        import win32con
        import win32gui
        import win32process
        import win32api
    except ImportError:
        print("警告: 无法导入 win32 模块，某些功能可能无法使用")
        win32con = None
        win32gui = None
        win32process = None
        win32api = None
else:
    win32con = None
    win32gui = None
    win32process = None
    win32api = None

# 配置常量
API_URL = "https://app.walkingcode.com/API/kill-domains.php"
DOMAINS_FILE = "domains.txt"
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
LOCALHOST_IP = "127.0.0.1"
CHECK_INTERVAL = 15  # 检查间隔（秒）
MARKER_START = "# === Kill Domains Start ==="
MARKER_END = "# === Kill Domains End ==="


class DomainKiller:
    def __init__(self):
        self.running = False
        self.icon = None
        self.current_domains = set()
        self.script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.domains_file = self.script_dir / DOMAINS_FILE
        
    def fetch_domains_from_api(self):
        """从 API 获取域名列表"""
        try:
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 200 and "data" in data:
                domains = data["data"].get("domains", [])
                return domains
            return []
        except Exception as e:
            print(f"获取域名列表失败: {e}")
            return []
    
    def update_domains_file(self, domains):
        """更新 domains.txt 文件"""
        try:
            with open(self.domains_file, 'w', encoding='utf-8') as f:
                for domain in domains:
                    f.write(f"{domain}\n")
            return True
        except Exception as e:
            print(f"更新 domains.txt 失败: {e}")
            return False
    
    def read_domains_file(self):
        """读取 domains.txt 文件"""
        domains = set()
        try:
            if self.domains_file.exists():
                with open(self.domains_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        domain = line.strip()
                        if domain and not domain.startswith('#'):
                            domains.add(domain)
        except Exception as e:
            print(f"读取 domains.txt 失败: {e}")
        return domains
    
    def read_hosts_file(self):
        """读取 hosts 文件内容"""
        try:
            with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"读取 hosts 文件失败: {e}")
            return ""
    
    def write_hosts_file(self, content):
        """写入 hosts 文件"""
        try:
            with open(HOSTS_PATH, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"写入 hosts 文件失败: {e}")
            return False
    
    def remove_old_rules(self, hosts_content):
        """移除旧的屏蔽规则"""
        lines = hosts_content.split('\n')
        new_lines = []
        in_block = False
        
        for line in lines:
            if MARKER_START in line:
                in_block = True
                continue
            if MARKER_END in line:
                in_block = False
                continue
            if not in_block:
                new_lines.append(line)
        
        return '\n'.join(new_lines).rstrip()
    
    def add_block_rules(self, hosts_content, domains):
        """添加屏蔽规则到 hosts 文件"""
        # 移除旧规则
        content = self.remove_old_rules(hosts_content)
        
        # 添加新规则
        if domains:
            content += f"\n\n{MARKER_START}\n"
            for domain in sorted(domains):
                content += f"{LOCALHOST_IP} {domain}\n"
            content += f"{MARKER_END}\n"
        
        return content
    
    def block_domains(self, domains):
        """屏蔽域名"""
        if not domains:
            return False
        
        try:
            # 读取当前 hosts 文件
            hosts_content = self.read_hosts_file()
            
            # 添加屏蔽规则
            new_content = self.add_block_rules(hosts_content, domains)
            
            # 写入 hosts 文件
            return self.write_hosts_file(new_content)
        except Exception as e:
            print(f"屏蔽域名失败: {e}")
            return False
    
    def restore_hosts(self):
        """恢复 hosts 文件，移除所有屏蔽规则"""
        try:
            hosts_content = self.read_hosts_file()
            new_content = self.remove_old_rules(hosts_content)
            return self.write_hosts_file(new_content)
        except Exception as e:
            print(f"恢复 hosts 文件失败: {e}")
            return False
    
    def sync_and_block(self):
        """同步域名并屏蔽"""
        # 从 API 获取最新域名列表
        api_domains = self.fetch_domains_from_api()
        
        if api_domains:
            # 更新 domains.txt
            self.update_domains_file(api_domains)
            self.current_domains = set(api_domains)
        else:
            # 如果 API 失败，从文件读取
            self.current_domains = self.read_domains_file()
        
        # 屏蔽域名
        if self.current_domains:
            self.block_domains(self.current_domains)
            print(f"已屏蔽 {len(self.current_domains)} 个域名")
    
    def check_and_update(self):
        """定时检查并更新"""
        while self.running:
            try:
                self.sync_and_block()
            except Exception as e:
                print(f"检查更新失败: {e}")
            
            # 等待指定时间
            for _ in range(CHECK_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)
    
    def create_tray_icon(self):
        """创建系统托盘图标"""
        # 创建简单的图标
        image = Image.new('RGB', (64, 64), color='red')
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 16, 48, 48], fill='white', outline='black', width=2)
        
        menu = pystray.Menu(
            pystray.MenuItem("立即同步", self.on_sync),
            pystray.MenuItem("恢复访问", self.on_restore),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.on_quit)
        )
        
        icon = pystray.Icon("DomainKiller", image, "网站访问控制", menu)
        return icon
    
    def on_sync(self, icon, item):
        """立即同步菜单项"""
        threading.Thread(target=self.sync_and_block, daemon=True).start()
    
    def on_restore(self, icon, item):
        """恢复访问菜单项"""
        threading.Thread(target=self.restore_hosts, daemon=True).start()
    
    def on_quit(self, icon, item):
        """退出程序"""
        self.running = False
        icon.stop()
    
    def hide_window(self):
        """隐藏控制台窗口（仅在 Windows 上）"""
        try:
            if sys.platform == 'win32' and win32gui:
                # 获取当前进程的窗口句柄
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    # 隐藏窗口
                    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
        except Exception as e:
            print(f"隐藏窗口失败: {e}")
    
    def run(self):
        """运行主程序"""
        # 隐藏窗口
        self.hide_window()
        
        # 首次同步
        self.sync_and_block()
        
        # 启动定时检查线程
        self.running = True
        check_thread = threading.Thread(target=self.check_and_update, daemon=True)
        check_thread.start()
        
        # 创建并运行系统托盘图标
        self.icon = self.create_tray_icon()
        self.icon.run()


def main():
    """主函数"""
    # 检查是否在 Windows 系统
    if sys.platform != 'win32':
        print("此程序仅支持 Windows 系统")
        return
    
    # 检查管理员权限（修改 hosts 文件需要）
    try:
        # 尝试写入 hosts 文件来检查权限
        test_path = HOSTS_PATH
        if not os.access(test_path, os.W_OK):
            print("警告: 可能需要管理员权限来修改 hosts 文件")
            print("请以管理员身份运行此程序")
    except Exception as e:
        print(f"权限检查失败: {e}")
    
    # 运行程序
    killer = DomainKiller()
    killer.run()


if __name__ == "__main__":
    main()

