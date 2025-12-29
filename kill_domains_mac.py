#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
macOS 网站访问控制程序
通过修改 hosts 文件屏蔽指定域名
支持 M1 ARM 和 Intel Mac
"""

import os
import sys
import json
import time
import threading
import requests
from pathlib import Path

# 尝试导入 pystray（系统托盘功能，可选）
try:
    import pystray
    from PIL import Image, ImageDraw
    Pystray_AVAILABLE = True
except ImportError:
    Pystray_AVAILABLE = False
    print("警告: pystray 未安装，系统托盘功能将不可用")

import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import plistlib

# 配置常量
API_URL = "https://app.walkingcode.com/API/kill-domains.php"
DOMAINS_FILE = "domains.txt"
HOSTS_PATH = "/etc/hosts"
LOCALHOST_IP = "127.0.0.1"
CHECK_INTERVAL = 60  # 检查间隔（秒）
MARKER_START = "# === Kill Domains Start ==="
MARKER_END = "# === Kill Domains End ==="
LAUNCH_AGENT_NAME = "com.domainkiller.plist"
LAUNCH_AGENT_DIR = Path.home() / "Library" / "LaunchAgents"
LAUNCH_AGENT_PATH = LAUNCH_AGENT_DIR / LAUNCH_AGENT_NAME


class DomainKiller:
    def __init__(self):
        self.running = False
        self.icon = None
        self.current_domains = set()
        self.script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.domains_file = self.script_dir / DOMAINS_FILE
        self.window = None
        self.window_thread = None
        self.password = None  # 保存从 API 获取的密码
        
        # 获取当前可执行文件路径（用于开机启动）
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 app
            self.exe_path = sys.executable
        else:
            # 如果是开发环境
            self.exe_path = os.path.abspath(__file__)
    
    def fetch_domains_from_api(self):
        """从 API 获取域名列表和密码
        返回: 成功返回 (domains, password) 元组，失败返回 None
        """
        try:
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 200 and "data" in data:
                domains = data["data"].get("domains", [])
                password = data.get("password", None)  # 获取密码
                return (domains, password)  # 返回元组
            else:
                # API 返回了数据，但格式不正确
                print(f"API 返回格式错误: {data}")
                return None  # 返回 None 表示失败
        except requests.exceptions.RequestException as e:
            # 网络错误
            print(f"获取域名列表失败（网络错误）: {e}")
            return None  # 返回 None 表示失败
        except Exception as e:
            # 其他错误
            print(f"获取域名列表失败: {e}")
            return None  # 返回 None 表示失败
    
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
    
    def get_sudo_password(self):
        """使用 osascript 获取 sudo 密码（非阻塞方式）"""
        try:
            # 使用 osascript 显示对话框，但不在主线程阻塞
            script = '''
            tell application "System Events"
                activate
                try
                    set theAnswer to display dialog "需要管理员权限来修改 hosts 文件" & return & return & "请输入您的管理员密码:" default answer "" buttons {"取消", "确定"} default button "确定" with hidden answer with icon caution
                    return text returned of theAnswer
                on error
                    return ""
                end try
            end tell
            '''
            # 使用 Popen 而不是 run，避免阻塞
            process = subprocess.Popen(
                ['osascript', '-e', script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # 等待最多 60 秒
            try:
                stdout, stderr = process.communicate(timeout=60)
                if process.returncode == 0 and stdout.strip():
                    return stdout.strip()
                return None
            except subprocess.TimeoutExpired:
                process.kill()
                print("密码输入超时")
                return None
        except Exception as e:
            print(f"获取密码失败: {e}")
            return None
    
    def read_hosts_file(self):
        """读取 hosts 文件内容（需要 sudo 权限）"""
        try:
            # 先尝试直接读取（如果已经有权限）
            try:
                with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
                    return f.read()
            except PermissionError:
                pass
            
            # 需要 sudo，使用密码（在后台线程中获取，避免阻塞）
            # 注意：这里简化处理，如果无法读取，返回空字符串
            # 实际使用时，应该在需要时才提示密码
            print("提示: 需要管理员权限读取 hosts 文件")
            print("请在需要时手动输入密码")
            
            # 暂时返回空，避免阻塞启动
            return ""
        except Exception as e:
            print(f"读取 hosts 文件失败: {e}")
            return ""
    
    def write_hosts_file(self, content):
        """写入 hosts 文件（需要 sudo 权限）"""
        try:
            # 先尝试直接写入（如果已经有权限）
            try:
                with open(HOSTS_PATH, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(content)
                return True
            except PermissionError:
                pass
            
            # 需要 sudo，使用密码
            password = self.get_sudo_password()
            if not password:
                error_msg = "用户取消了密码输入"
                print(error_msg)
                if self.window:
                    self.show_error_in_window(error_msg)
                return False
            
            # 使用 sudo -S tee 写入 hosts 文件
            process = subprocess.Popen(
                ['sudo', '-S', 'tee', HOSTS_PATH],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # 先发送密码，然后发送内容
            input_data = password + '\n' + content
            stdout, stderr = process.communicate(input=input_data, timeout=10)
            
            if process.returncode == 0:
                return True
            else:
                error_msg = f"写入 hosts 文件失败: {stderr}"
                print(error_msg)
                if self.window:
                    self.show_error_in_window(error_msg)
                return False
        except subprocess.TimeoutExpired:
            error_msg = "写入 hosts 文件超时"
            print(error_msg)
            if self.window:
                self.show_error_in_window(error_msg)
            return False
        except Exception as e:
            error_msg = f"写入 hosts 文件失败: {e}"
            print(error_msg)
            if self.window:
                self.show_error_in_window(error_msg)
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
            # 如果没有域名，清除所有屏蔽规则
            return self.restore_hosts()
        
        try:
            # 读取当前 hosts 文件
            hosts_content = self.read_hosts_file()
            
            # 添加屏蔽规则（会自动移除旧规则）
            new_content = self.add_block_rules(hosts_content, domains)
            
            # 写入 hosts 文件
            result = self.write_hosts_file(new_content)
            
            if result:
                # 更新当前域名列表（确保同步）
                self.current_domains = set(domains)
                # 更新窗口显示
                if self.window:
                    self.update_window_domains()
            
            return result
        except Exception as e:
            error_msg = f"屏蔽域名失败: {e}"
            print(error_msg)
            if "Permission" in str(e) or "denied" in str(e).lower():
                error_msg += "\n\n请确保有 sudo 权限！"
            if self.window:
                self.show_error_in_window(error_msg)
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
    
    def startup_block(self):
        """启动时立即从本地文件读取并屏蔽（不等待 API）"""
        try:
            # 从本地文件读取域名
            self.current_domains = self.read_domains_file()
            
            if self.current_domains:
                # 有域名需要屏蔽
                success = self.block_domains(self.current_domains)
                if success:
                    msg = f"启动时已屏蔽 {len(self.current_domains)} 个域名（来自本地文件）"
                    print(msg)
                    if self.window:
                        self.update_status_in_window(msg)
                        self.update_window_domains()
                else:
                    msg = "启动时屏蔽域名失败，将在首次同步时重试"
                    print(msg)
                    if self.window:
                        self.update_status_in_window(msg)
            else:
                # 本地文件为空，显示状态
                msg = "启动时：本地文件为空，等待同步"
                print(msg)
                if self.window:
                    self.update_status_in_window(msg)
        except Exception as e:
            print(f"启动时处理失败: {e}")
            if self.window:
                self.update_status_in_window(f"启动错误: {e}", error=True)
    
    def extract_domains_from_hosts(self, hosts_content):
        """从 hosts 文件内容中提取被屏蔽的域名"""
        domains = set()
        lines = hosts_content.split('\n')
        in_block = False
        
        for line in lines:
            if MARKER_START in line:
                in_block = True
                continue
            if MARKER_END in line:
                in_block = False
                continue
            if in_block:
                # 解析格式: 127.0.0.1 domain.com
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0] == LOCALHOST_IP:
                    domain = parts[1].strip()
                    if domain:
                        domains.add(domain)
        
        return domains
    
    def sync_and_block(self):
        """同步域名并屏蔽（从 API 获取最新域名）"""
        # 从 API 获取最新域名列表和密码
        api_result = self.fetch_domains_from_api()
        
        # 判断 API 是否成功（区分 API 失败和返回空列表）
        # api_result 为 None 表示 API 调用失败，为元组 (domains, password) 表示成功
        api_success = api_result is not None
        
        if api_success:
            # API 调用成功（可能返回空列表）
            api_domains, api_password = api_result
            # 保存密码
            if api_password:
                self.password = api_password
            # 更新 domains.txt（即使为空也要更新，保持同步）
            self.update_domains_file(api_domains)
            self.current_domains = set(api_domains)
        else:
            # API 调用失败（网络错误等），从文件读取
            self.current_domains = self.read_domains_file()
            if not self.current_domains:
                # API 失败且本地文件为空，保持当前屏蔽状态不变
                msg = "API 获取失败，保持当前屏蔽状态"
                print(msg)
                if self.window:
                    self.update_status_in_window(msg)
                return
        
        # 屏蔽域名（即使为空也要处理，清除之前的屏蔽规则）
        if self.current_domains:
            # 有域名需要屏蔽
            success = self.block_domains(self.current_domains)
            if success:
                msg = f"已同步并屏蔽 {len(self.current_domains)} 个域名"
                print(msg)
                if self.window:
                    self.update_status_in_window(msg)
                    self.update_window_domains()
            else:
                msg = "同步后屏蔽域名失败，请检查是否有 sudo 权限"
                print(msg)
                if self.window:
                    self.update_status_in_window(msg, error=True)
        else:
            # 没有域名需要屏蔽，清除所有屏蔽规则
            success = self.restore_hosts()
            if success:
                msg = "当前没有需要屏蔽的域名，已清除所有屏蔽规则"
                print(msg)
                if self.window:
                    self.update_status_in_window(msg)
                    self.update_window_domains()
            else:
                msg = "清除屏蔽规则失败，请检查是否有 sudo 权限"
                print(msg)
                if self.window:
                    self.update_status_in_window(msg, error=True)
    
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
        if not Pystray_AVAILABLE:
            print("系统托盘功能不可用（pystray 未安装）")
            return None
        
        try:
            # 创建简单的图标
            image = Image.new('RGB', (64, 64), color='red')
            draw = ImageDraw.Draw(image)
            draw.ellipse([16, 16, 48, 48], fill='white', outline='black', width=2)
            
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self.on_show_window),
                pystray.MenuItem("立即同步", self.on_sync),
                pystray.MenuItem("恢复访问", self.on_restore),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self.on_quit)
            )
            
            icon = pystray.Icon("DomainKiller", image, "网站访问控制", menu)
            return icon
        except Exception as e:
            print(f"创建系统托盘图标失败: {e}")
            return None
    
    def on_show_window(self, icon, item):
        """显示窗口菜单项"""
        if self.window is None or not self.window.winfo_exists():
            self.create_window()
        else:
            try:
                self.window.lift()
                self.window.deiconify()
            except:
                self.create_window()
    
    def on_sync(self, icon, item):
        """立即同步菜单项"""
        threading.Thread(target=self.sync_and_block, daemon=True).start()
    
    def on_restore_from_window(self):
        """从主窗口恢复访问（需要密码验证）"""
        # 从主窗口的密码输入框获取密码
        if not self.window:
            return
        
        try:
            input_password = self.password_entry.get()
            
            if not input_password:
                # 密码为空
                import tkinter.messagebox as messagebox
                messagebox.showwarning("警告", "请输入密码！")
                return
            
            # 更新状态
            if self.window:
                self.update_status_in_window("正在验证密码...")
            
            # 调用API验证密码
            success, message = self.verify_password_with_api(input_password)
            
            if success:
                # 密码正确，恢复访问
                if self.window:
                    self.update_status_in_window("密码正确，正在恢复访问...")
                
                # 恢复hosts文件（解除屏蔽）
                restore_success = self.restore_hosts()
                if restore_success:
                    # 恢复访问后，清空当前域名列表
                    self.current_domains = set()
                    # 注意：不删除 domains.txt 文件，保留域名列表以便下次同步使用
                    if self.window:
                        self.update_window_domains()
                        self.update_status_in_window("已恢复所有网站访问")
                    # 清空密码输入框
                    self.password_entry.delete(0, tk.END)
                else:
                    msg = "恢复访问失败，请检查是否有 sudo 权限"
                    if self.window:
                        self.update_status_in_window(msg, error=True)
            else:
                # 密码错误
                import tkinter.messagebox as messagebox
                messagebox.showerror("错误", f"密码验证失败: {message}")
                # 清空密码输入框
                self.password_entry.delete(0, tk.END)
                if self.window:
                    self.update_status_in_window("密码验证失败")
        except Exception as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("错误", f"恢复访问失败: {e}")
            print(f"恢复访问失败: {e}")
    
    def _restore_hosts(self):
        """内部恢复函数（从托盘菜单调用，需要密码验证）"""
        # 显示窗口以便输入密码
        if self.window:
            try:
                self.window.lift()
                self.window.deiconify()
                # 聚焦到密码输入框
                self.password_entry.focus()
            except:
                self.create_window()
        else:
            self.create_window()
        
        # 提示用户在主窗口输入密码
        try:
            import tkinter.messagebox as messagebox
            messagebox.showinfo("提示", "请在主窗口的密码输入框中输入密码，然后点击\"恢复访问\"按钮。")
        except:
            print("请在主窗口的密码输入框中输入密码，然后点击\"恢复访问\"按钮。")
    
    def on_restore(self, icon, item):
        """恢复访问菜单项"""
        threading.Thread(target=self._restore_hosts, daemon=True).start()
    
    def verify_password_with_api(self, input_password):
        """调用API验证密码
        返回: (success, message) 元组，success为True表示密码正确
        """
        try:
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 200:
                api_password = data.get("password", None)
                if api_password and input_password == api_password:
                    return (True, "密码验证成功")
                else:
                    return (False, "密码错误")
            else:
                return (False, f"API返回错误: {data.get('message', '未知错误')}")
        except requests.exceptions.RequestException as e:
            return (False, f"网络错误: {str(e)}")
        except Exception as e:
            return (False, f"验证失败: {str(e)}")
    
    def on_quit_from_window(self):
        """从主窗口退出程序（需要密码验证）"""
        # 从主窗口的密码输入框获取密码
        if not self.window:
            return
        
        try:
            input_password = self.password_entry.get()
            
            if not input_password:
                # 密码为空
                import tkinter.messagebox as messagebox
                messagebox.showwarning("警告", "请输入密码！")
                return
            
            # 更新状态
            if self.window:
                self.update_status_in_window("正在验证密码...")
            
            # 调用API验证密码
            success, message = self.verify_password_with_api(input_password)
            
            if success:
                # 密码正确，先解除屏蔽，然后退出
                if self.window:
                    self.update_status_in_window("密码正确，正在解除屏蔽...")
                
                # 恢复hosts文件（解除屏蔽）
                restore_success = self.restore_hosts()
                if restore_success:
                    if self.window:
                        self.update_status_in_window("已解除屏蔽，正在退出...")
                    # 等待一下让用户看到消息
                    time.sleep(0.5)
                    self._do_quit_from_window()
                else:
                    # 恢复失败，但仍然退出
                    import tkinter.messagebox as messagebox
                    messagebox.showwarning("警告", "密码验证成功，但解除屏蔽失败。程序仍将退出。")
                    self._do_quit_from_window()
            else:
                # 密码错误
                import tkinter.messagebox as messagebox
                messagebox.showerror("错误", f"密码验证失败: {message}")
                # 清空密码输入框
                self.password_entry.delete(0, tk.END)
                if self.window:
                    self.update_status_in_window("密码验证失败")
        except Exception as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("错误", f"退出验证失败: {e}")
            print(f"退出验证失败: {e}")
    
    def on_quit(self, icon, item):
        """从托盘菜单退出程序（需要密码验证）"""
        # 显示窗口以便输入密码
        if self.window:
            try:
                self.window.lift()
                self.window.deiconify()
                # 聚焦到密码输入框
                self.password_entry.focus()
            except:
                self.create_window()
        else:
            self.create_window()
        
        # 提示用户在主窗口输入密码
        try:
            import tkinter.messagebox as messagebox
            messagebox.showinfo("提示", "请在主窗口的密码输入框中输入密码，然后点击\"退出程序\"按钮。")
        except:
            print("请在主窗口的密码输入框中输入密码，然后点击\"退出程序\"按钮。")
    
    def _do_quit(self, icon):
        """执行退出操作（从托盘菜单）"""
        self.running = False
        if self.window:
            try:
                self.window.quit()
                self.window.destroy()
            except:
                pass
        if icon:
            icon.stop()
    
    def _do_quit_from_window(self):
        """执行退出操作（从主窗口）"""
        self.running = False
        if self.window:
            try:
                self.window.quit()
                self.window.destroy()
            except:
                pass
        if self.icon:
            self.icon.stop()
    
    def create_window(self):
        """创建显示窗口（必须在主线程调用）"""
        try:
            if self.window is not None:
                try:
                    if self.window.winfo_exists():
                        return
                except:
                    # 窗口已销毁，重新创建
                    self.window = None
            
            # 直接在主线程创建窗口
            self.window = tk.Tk()
        except Exception as e:
            print(f"创建窗口失败: {e}")
            return
        
        try:
            self.window.title("网站访问控制 - 屏蔽域名列表")
            self.window.geometry("600x500")
            self.window.resizable(True, True)
            
            # 状态栏
            status_frame = ttk.Frame(self.window, padding="10")
            status_frame.pack(fill=tk.X, padx=5, pady=5)
            
            self.status_label = ttk.Label(
                status_frame, 
                text="状态: 正在加载...",
                font=("Arial", 10)
            )
            self.status_label.pack(side=tk.LEFT)
            
            # 域名数量标签
            self.count_label = ttk.Label(
                status_frame,
                text="",
                font=("Arial", 10, "bold"),
                foreground="blue"
            )
            self.count_label.pack(side=tk.RIGHT)
            
            # 按钮框架
            button_frame = ttk.Frame(self.window, padding="5")
            button_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Button(
                button_frame,
                text="立即同步",
                command=lambda: threading.Thread(target=self.sync_and_block, daemon=True).start()
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                button_frame,
                text="刷新列表",
                command=self.update_window_domains
            ).pack(side=tk.LEFT, padx=5)
            
            # 域名列表框架（缩小）
            list_frame = ttk.Frame(self.window, padding="5")
            list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 标签
            ttk.Label(
                list_frame,
                text="当前屏蔽的域名列表:",
                font=("Arial", 10, "bold")
            ).pack(anchor=tk.W, pady=(0, 5))
            
            # 域名列表文本框（只读，缩小高度）
            self.domains_text = scrolledtext.ScrolledText(
                list_frame,
                wrap=tk.WORD,
                font=("Consolas", 10),
                state=tk.DISABLED,
                bg="#f5f5f5",
                height=8  # 设置固定高度，缩小显示区域
            )
            self.domains_text.pack(fill=tk.BOTH, expand=False)
            
            # 密码和设置框架
            password_frame = ttk.Frame(self.window, padding="5")
            password_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
            
            # 左侧：密码输入
            password_left = ttk.Frame(password_frame)
            password_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            ttk.Label(
                password_left,
                text="密码:",
                font=("Arial", 9)
            ).pack(side=tk.LEFT, padx=(0, 5))
            
            # 密码输入框
            self.password_entry = ttk.Entry(
                password_left,
                show='*',
                font=("Arial", 10),
                width=20
            )
            self.password_entry.pack(side=tk.LEFT, padx=5)
            
            # 恢复访问按钮（需要密码）
            ttk.Button(
                password_left,
                text="恢复访问",
                command=self.on_restore_from_window
            ).pack(side=tk.LEFT, padx=5)
            
            # 退出按钮
            ttk.Button(
                password_left,
                text="退出程序",
                command=self.on_quit_from_window
            ).pack(side=tk.LEFT, padx=5)
            
            # 右侧：开机启动选项
            startup_frame = ttk.Frame(password_frame)
            startup_frame.pack(side=tk.RIGHT, padx=10)
            
            # 开机启动复选框
            self.startup_var = tk.BooleanVar()
            # 检查当前是否已设置开机启动
            self.startup_var.set(self.is_startup_enabled())
            
            startup_checkbox = ttk.Checkbutton(
                startup_frame,
                text="开机启动",
                variable=self.startup_var,
                command=self.toggle_startup
            )
            startup_checkbox.pack(side=tk.LEFT)
            
            # 提示信息
            info_label = ttk.Label(
                self.window,
                text="提示: 程序会在后台自动同步域名列表，每60秒检查一次更新",
                font=("Arial", 9),
                foreground="gray"
            )
            info_label.pack(side=tk.BOTTOM, pady=5)
            
            # 窗口关闭事件
            def on_closing():
                try:
                    self.window.withdraw()  # 隐藏窗口而不是关闭
                except:
                    pass
            
            try:
                self.window.protocol("WM_DELETE_WINDOW", on_closing)
            except:
                pass
            
            # 初始化显示
            try:
                self.update_window_domains()
            except Exception as e:
                print(f"初始化窗口显示失败: {e}")
            
            # 确保窗口创建完成
            try:
                self.window.update_idletasks()
            except:
                pass
        except Exception as e:
            print(f"创建窗口组件失败: {e}")
            import traceback
            traceback.print_exc()
    
    def update_window_domains(self):
        """更新窗口中的域名列表"""
        if self.window is None:
            return
        
        try:
            # 更新当前域名列表
            self.current_domains = self.read_domains_file()
            
            # 更新文本框
            self.domains_text.config(state=tk.NORMAL)
            self.domains_text.delete(1.0, tk.END)
            
            if self.current_domains:
                domains_list = sorted(self.current_domains)
                for i, domain in enumerate(domains_list, 1):
                    self.domains_text.insert(tk.END, f"{i}. {domain}\n")
            else:
                self.domains_text.insert(tk.END, "当前没有屏蔽任何域名\n")
            
            self.domains_text.config(state=tk.DISABLED)
            
            # 更新计数标签
            count = len(self.current_domains)
            self.count_label.config(text=f"共 {count} 个域名" if count > 0 else "")
            
        except Exception as e:
            print(f"更新窗口失败: {e}")
    
    def update_status_in_window(self, message, error=False):
        """更新窗口状态栏"""
        if self.window is None:
            return
        
        try:
            color = "red" if error else "green"
            self.status_label.config(text=f"状态: {message}", foreground=color)
        except:
            pass
    
    def show_error_in_window(self, message):
        """在窗口中显示错误信息"""
        if self.window is None:
            return
        
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror("错误", message)
        except:
            pass
    
    def is_startup_enabled(self):
        """检查是否已设置开机启动"""
        try:
            return LAUNCH_AGENT_PATH.exists()
        except Exception as e:
            print(f"检查开机启动失败: {e}")
            return False
    
    def toggle_startup(self):
        """切换开机启动状态"""
        try:
            if self.startup_var.get():
                # 启用开机启动
                self.enable_startup()
            else:
                # 禁用开机启动
                self.disable_startup()
        except Exception as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("错误", f"设置开机启动失败: {e}")
            # 恢复复选框状态
            self.startup_var.set(not self.startup_var.get())
    
    def enable_startup(self):
        """启用开机启动（使用 LaunchAgent）"""
        try:
            # 确保 LaunchAgents 目录存在
            LAUNCH_AGENT_DIR.mkdir(parents=True, exist_ok=True)
            
            # 获取可执行文件路径
            if getattr(sys, 'frozen', False):
                # 如果是打包后的可执行文件
                app_path = sys.executable
                # 如果是 app bundle，需要找到实际的可执行文件
                if app_path.endswith('.app'):
                    # 查找 app bundle 内的可执行文件
                    app_name = os.path.basename(app_path).replace('.app', '')
                    executable_path = os.path.join(app_path, 'Contents', 'MacOS', app_name)
                    if os.path.exists(executable_path):
                        app_path = executable_path
                program_args = [app_path]
            else:
                # 如果是开发环境，使用 Python 解释器运行脚本
                python_path = sys.executable
                script_path = os.path.abspath(__file__)
                program_args = [python_path, script_path]
            
            # 创建 plist 文件
            plist_data = {
                'Label': 'com.domainkiller',
                'ProgramArguments': program_args,
                'RunAtLoad': True,
                'KeepAlive': False,
            }
            
            # 写入 plist 文件
            with open(LAUNCH_AGENT_PATH, 'wb') as f:
                plistlib.dump(plist_data, f)
            
            # 加载 LaunchAgent（使用 launchctl load -w 确保立即生效）
            result = subprocess.run(
                ['launchctl', 'load', '-w', str(LAUNCH_AGENT_PATH)],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                print(f"加载 LaunchAgent 警告: {result.stderr}")
            
            print(f"已启用开机启动: {LAUNCH_AGENT_PATH}")
            return True
        except Exception as e:
            print(f"启用开机启动失败: {e}")
            return False
    
    def disable_startup(self):
        """禁用开机启动"""
        try:
            if LAUNCH_AGENT_PATH.exists():
                # 卸载 LaunchAgent（使用 launchctl unload -w）
                result = subprocess.run(
                    ['launchctl', 'unload', '-w', str(LAUNCH_AGENT_PATH)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                # 删除 plist 文件
                try:
                    LAUNCH_AGENT_PATH.unlink()
                except Exception as e:
                    print(f"删除 plist 文件失败: {e}")
            
            print("已禁用开机启动")
            return True
        except Exception as e:
            print(f"禁用开机启动失败: {e}")
            return False
    
    def run(self):
        """运行主程序"""
        try:
            # 创建并显示窗口（必须在主线程）
            self.create_window()
            
            if not self.window:
                print("错误: 无法创建窗口")
                return
            
            # 启动定时检查线程
            self.running = True
            
            # 启动时立即从本地文件读取并屏蔽（在后台线程，避免阻塞）
            def startup_in_background():
                try:
                    time.sleep(0.5)  # 等待窗口完全显示
                    self.startup_block()
                except Exception as e:
                    print(f"启动时处理失败: {e}")
                    if self.window:
                        try:
                            self.update_status_in_window(f"启动错误: {e}", error=True)
                        except:
                            pass
            
            threading.Thread(target=startup_in_background, daemon=True).start()
            
            # 首次同步（在后台尝试从 API 获取最新域名）
            def sync_in_background():
                try:
                    self.sync_and_block()
                except Exception as e:
                    print(f"同步失败: {e}")
            
            threading.Thread(target=sync_in_background, daemon=True).start()
            
            # 启动定时检查线程
            def check_in_background():
                try:
                    self.check_and_update()
                except Exception as e:
                    print(f"定时检查失败: {e}")
            
            check_thread = threading.Thread(target=check_in_background, daemon=True)
            check_thread.start()
            
            # 创建并运行系统托盘图标（如果可用）
            try:
                self.icon = self.create_tray_icon()
                if self.icon:
                    # 在后台线程运行系统托盘
                    def run_icon():
                        try:
                            self.icon.run()
                        except Exception as e:
                            print(f"系统托盘运行失败: {e}")
                    icon_thread = threading.Thread(target=run_icon, daemon=True)
                    icon_thread.start()
            except Exception as e:
                print(f"创建系统托盘失败: {e}")
            
            # 运行窗口主循环（必须在主线程）
            if self.window:
                self.window.mainloop()
        except Exception as e:
            import traceback
            print(f"运行程序时发生错误: {e}")
            print(traceback.format_exc())
            raise


def main():
    """主函数"""
    try:
        # 检查是否在 macOS 系统
        if sys.platform != 'darwin':
            print("此程序仅支持 macOS 系统")
            return
        
        # 检查 sudo 权限提示
        print("提示: 修改 hosts 文件需要 sudo 权限，程序运行时会提示输入密码")
        
        # 运行程序
        killer = DomainKiller()
        killer.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        # 捕获所有异常，显示错误信息
        import traceback
        error_msg = f"程序发生错误: {e}\n\n详细错误信息:\n{traceback.format_exc()}"
        print(error_msg)
        
        # 尝试显示错误对话框
        try:
            import tkinter.messagebox as messagebox
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            messagebox.showerror("程序错误", f"程序发生错误:\n{e}\n\n请查看控制台获取详细信息")
            root.destroy()
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()

