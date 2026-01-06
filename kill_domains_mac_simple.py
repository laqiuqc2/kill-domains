#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
macOS 网站访问控制程序 - 实时拦截版
使用 hosts 文件 + pfctl 防火墙实现实时拦截
支持 M1 ARM 和 Intel Mac
实时生效，不受浏览器缓存影响
"""

import os
import sys
import time
import threading
import requests
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# 配置常量
API_URL = "https://app.walkingcode.com/API/kill-domains.php"
DOMAINS_FILE = "domains.txt"
HOSTS_PATH = "/etc/hosts"
LOCALHOST_IP = "127.0.0.1"
CHECK_INTERVAL = 60
MARKER_START = "# === Kill Domains Start ==="
MARKER_END = "# === Kill Domains End ==="
PFCTL_RULES_FILE = "/tmp/domainkiller_pfctl_rules.conf"
PROXY_PORT = 8888  # 本地代理服务器端口


class BlockingProxyHandler(BaseHTTPRequestHandler):
    """HTTP 代理服务器处理器 - 拦截被屏蔽的域名"""
    
    blocked_domains = set()  # 被屏蔽的域名集合
    
    def do_GET(self):
        """处理 GET 请求"""
        self.handle_request()
    
    def do_POST(self):
        """处理 POST 请求"""
        self.handle_request()
    
    def do_CONNECT(self):
        """处理 HTTPS CONNECT 请求"""
        self.handle_https_request()
    
    def handle_request(self):
        """处理 HTTP 请求"""
        try:
            # 解析请求 URL
            url = self.path
            if url.startswith('http://'):
                parsed = urlparse(url)
            else:
                parsed = urlparse('http://' + url)
            
            host = parsed.netloc or parsed.path.split('/')[0]
            if ':' in host:
                host = host.split(':')[0]
            
            # 检查域名是否被屏蔽
            if self.is_blocked(host):
                self.send_blocked_response()
                return
            
            # 转发请求到目标服务器
            self.forward_request()
        except Exception as e:
            print(f"代理处理请求错误: {e}")
            self.send_error(500, str(e))
    
    def handle_https_request(self):
        """处理 HTTPS CONNECT 请求"""
        try:
            # CONNECT 请求格式: CONNECT host:port HTTP/1.1
            host_port = self.path.split(' ')[0] if ' ' in self.path else self.path
            host = host_port.split(':')[0]
            
            # 检查域名是否被屏蔽
            if self.is_blocked(host):
                self.send_blocked_response()
                return
            
            # 转发 CONNECT 请求
            self.forward_https_request(host_port)
        except Exception as e:
            print(f"代理处理 HTTPS 请求错误: {e}")
            self.send_error(500, str(e))
    
    def is_blocked(self, host):
        """检查域名是否被屏蔽"""
        if not host:
            return False
        
        # 检查完整域名
        if host in self.blocked_domains:
            return True
        
        # 检查域名变体（如 www.domain.com 和 domain.com）
        parts = host.split('.')
        if len(parts) >= 2:
            # 检查去掉 www 后的域名
            if parts[0] == 'www' and len(parts) > 2:
                base_domain = '.'.join(parts[1:])
                if base_domain in self.blocked_domains:
                    return True
            # 检查添加 www 后的域名
            www_domain = 'www.' + host
            if www_domain in self.blocked_domains:
                return True
        
        return False
    
    def send_blocked_response(self):
        """发送屏蔽响应"""
        self.send_response(403)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        blocked_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>网站已被屏蔽</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                h1 { color: #d32f2f; }
            </style>
        </head>
        <body>
            <h1>🚫 网站已被屏蔽</h1>
            <p>该网站已被管理员屏蔽，无法访问。</p>
        </body>
        </html>
        """
        self.wfile.write(blocked_html.encode('utf-8'))
    
    def forward_request(self):
        """转发 HTTP 请求到目标服务器"""
        try:
            # 解析目标 URL
            url = self.path
            if not url.startswith('http://'):
                url = 'http://' + url
            
            parsed = urlparse(url)
            host = parsed.netloc or parsed.path.split('/')[0]
            port = 80
            if ':' in host:
                host, port_str = host.split(':')
                port = int(port_str)
            
            # 连接到目标服务器
            try:
                target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target_socket.settimeout(10)
                target_socket.connect((host, port))
                
                # 构建请求
                request_line = f"{self.command} {parsed.path or '/'} HTTP/1.1\r\n"
                headers = f"Host: {host}\r\n"
                headers += "Connection: close\r\n"
                
                # 转发原始请求头（除了 Host）
                for header, value in self.headers.items():
                    if header.lower() != 'host' and header.lower() != 'connection':
                        headers += f"{header}: {value}\r\n"
                
                request = request_line + headers + "\r\n"
                
                # 发送请求
                target_socket.sendall(request.encode())
                
                # 接收响应并转发
                response_data = b''
                while True:
                    chunk = target_socket.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
                
                target_socket.close()
                
                # 发送响应给客户端
                self.wfile.write(response_data)
            except Exception as e:
                print(f"转发请求失败: {e}")
                self.send_error(502, f"Proxy error: {str(e)}")
        except Exception as e:
            print(f"转发请求异常: {e}")
            self.send_error(502, f"Proxy error: {str(e)}")
    
    def forward_https_request(self, host_port):
        """转发 HTTPS CONNECT 请求"""
        try:
            # 解析目标地址
            if ':' in host_port:
                host, port_str = host_port.split(':')
                port = int(port_str)
            else:
                host = host_port
                port = 443
            
            # 连接到目标服务器
            try:
                target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target_socket.settimeout(10)
                target_socket.connect((host, port))
                
                # 发送 200 Connection Established 响应
                self.send_response(200, 'Connection Established')
                self.end_headers()
                
                # 建立双向隧道（使用线程）
                import threading
                client_socket = self.connection
                tunnel_active = threading.Event()
                tunnel_active.set()
                
                def forward_to_target():
                    try:
                        while tunnel_active.is_set():
                            data = client_socket.recv(4096)
                            if not data:
                                break
                            target_socket.sendall(data)
                    except:
                        pass
                    finally:
                        tunnel_active.clear()
                
                def forward_to_client():
                    try:
                        while tunnel_active.is_set():
                            data = target_socket.recv(4096)
                            if not data:
                                break
                            client_socket.sendall(data)
                    except:
                        pass
                    finally:
                        tunnel_active.clear()
                
                # 启动转发线程
                t1 = threading.Thread(target=forward_to_target, daemon=True)
                t2 = threading.Thread(target=forward_to_client, daemon=True)
                t1.start()
                t2.start()
                
                # 等待线程结束
                t1.join(timeout=300)  # 5分钟超时
                t2.join(timeout=300)
                tunnel_active.clear()
                target_socket.close()
            except Exception as e:
                print(f"转发 HTTPS 请求失败: {e}")
                self.send_error(502, f"HTTPS Proxy error: {str(e)}")
        except Exception as e:
            print(f"转发 HTTPS 请求异常: {e}")
            self.send_error(502, f"HTTPS Proxy error: {str(e)}")
    
    def log_message(self, format, *args):
        """禁用默认日志输出"""
        pass


class DomainKiller:
    def __init__(self):
        self.running = False
        self.current_domains = set()
        
        # 确定文件目录：打包后使用 .app 所在目录，开发模式使用脚本目录
        if getattr(sys, 'frozen', False):
            # 打包后的应用：使用 .app 所在目录
            # sys.executable 指向 .app/Contents/MacOS/DomainKiller
            # 所以 .app 目录是 parent.parent.parent
            app_path = Path(sys.executable)
            if '.app' in str(app_path):
                # .app/Contents/MacOS/DomainKiller -> .app 目录
                app_dir = app_path.parent.parent.parent
                # 使用 .app 目录（与 .app 文件同级）
                self.script_dir = app_dir
            else:
                # 如果不是 .app，使用可执行文件所在目录
                self.script_dir = app_path.parent
        else:
            # 开发模式：使用脚本所在目录
            if '__file__' in globals():
                self.script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            else:
                self.script_dir = Path.cwd()
        
        self.domains_file = self.script_dir / DOMAINS_FILE
        print(f"域名文件路径: {self.domains_file}")
        
        # 如果是打包后的应用，检查是否需要从打包资源复制文件
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # 检查打包资源中是否有 domains.txt
            bundled_file = Path(sys._MEIPASS) / DOMAINS_FILE
            if bundled_file.exists() and not self.domains_file.exists():
                try:
                    # 从打包资源复制到 .app 目录
                    import shutil
                    shutil.copy2(bundled_file, self.domains_file)
                    print(f"从打包资源复制 domains.txt 到: {self.domains_file}")
                except Exception as e:
                    print(f"复制打包资源失败: {e}")
        
        # 如果文件不存在，创建空文件（在 .app 目录中）
        if not self.domains_file.exists():
            try:
                self.domains_file.parent.mkdir(parents=True, exist_ok=True)
                # 创建带注释的空文件
                with open(self.domains_file, 'w', encoding='utf-8') as f:
                    f.write("# 本地域名列表，每行一个域名\n")
                print(f"创建空的域名文件: {self.domains_file}")
            except Exception as e:
                print(f"创建域名文件失败: {e}")
        self.window = None
        self.password = None
        self.sudo_password = None  # 缓存 sudo 密码（仅在内存中）
        self.use_pfctl = True  # 使用 pfctl 实现实时拦截
        self.api_domains = set()  # API 同步的域名列表（当前正在屏蔽的）
        self.proxy_server = None  # 代理服务器实例
        self.proxy_thread = None  # 代理服务器线程
        self.use_proxy = True  # 使用代理服务器拦截（对 Safari 更有效）
        
    def fetch_domains_from_api(self):
        """从 API 获取域名列表和密码"""
        try:
            print(f"正在连接 API: {API_URL}")
            response = requests.get(API_URL, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 200 and "data" in data:
                raw_domains = data["data"].get("domains", [])
                password = data.get("password", None)
                
                # 清理域名：去除协议前缀（http://, https://）和尾部斜杠
                cleaned_domains = []
                for domain in raw_domains:
                    # 去除首尾空白
                    domain = domain.strip()
                    if not domain:
                        continue
                    
                    # 去除协议前缀
                    if domain.startswith("http://"):
                        domain = domain[7:]
                    elif domain.startswith("https://"):
                        domain = domain[8:]
                    
                    # 去除尾部斜杠和路径
                    if "/" in domain:
                        domain = domain.split("/")[0]
                    
                    # 去除尾部空白和斜杠
                    domain = domain.rstrip("/").strip()
                    
                    if domain:
                        cleaned_domains.append(domain)
                
                print(f"✅ API 返回: {len(raw_domains)} 个原始域名，清理后 {len(cleaned_domains)} 个有效域名")
                return (cleaned_domains, password)
            else:
                print(f"⚠️ API 返回错误: {data.get('code', 'unknown')}")
                return None
        except requests.exceptions.Timeout:
            print(f"⚠️ API 请求超时（超过 15 秒）")
            return None
        except requests.exceptions.RequestException as e:
            print(f"⚠️ API 请求失败: {e}")
            return None
        except Exception as e:
            print(f"⚠️ 获取域名列表失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
    
    def read_hosts_file(self, silent=False):
        """读取 hosts 文件内容
        silent: 如果为 True，不会弹出密码对话框，直接返回空字符串
        """
        try:
            # 尝试直接读取
            with open(HOSTS_PATH, 'r', encoding='utf-8') as f:
                return f.read()
        except PermissionError:
            # 需要 sudo
            if silent:
                # 静默模式：如果有缓存的密码就使用，没有就返回空
                if self.sudo_password:
                    try:
                        process = subprocess.Popen(
                            ['sudo', '-S', 'cat', HOSTS_PATH],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        stdout, stderr = process.communicate(input=self.sudo_password + '\n', timeout=10)
                        if process.returncode == 0:
                            return stdout
                        # 密码失效，清除缓存
                        self.sudo_password = None
                    except:
                        self.sudo_password = None
                return ""
            
            # 非静默模式：获取密码（使用缓存）
            password = self.get_sudo_password("需要管理员权限读取 hosts 文件", use_cache=True)
            if not password:
                return ""
            
            try:
                process = subprocess.Popen(
                    ['sudo', '-S', 'cat', HOSTS_PATH],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=password + '\n', timeout=10)
                if process.returncode == 0:
                    return stdout
                # 如果失败，清除缓存的密码
                self.sudo_password = None
                return ""
            except:
                self.sudo_password = None
                return ""
        except Exception as e:
            print(f"读取 hosts 文件失败: {e}")
            return ""
    
    def get_sudo_password(self, message="需要管理员权限", use_cache=True):
        """使用 osascript 获取 sudo 密码（支持缓存）"""
        # 如果已有缓存的密码，先验证是否仍然有效
        if use_cache and self.sudo_password:
            if self.verify_sudo_password(self.sudo_password):
                return self.sudo_password
            else:
                # 密码已失效，清除缓存
                self.sudo_password = None
        
        # 获取新密码
        try:
            script = f'''
            tell application "System Events"
                activate
                try
                    set theAnswer to display dialog "{message}" & return & return & "请输入您的MACOS管理员密码:" default answer "" buttons {{"取消", "确定"}} default button "确定" with hidden answer with icon caution
                    return text returned of theAnswer
                on error
                    return ""
                end try
            end tell
            '''
            process = subprocess.Popen(
                ['osascript', '-e', script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=60)
            if process.returncode == 0 and stdout.strip():
                password = stdout.strip()
                # 缓存密码（仅在内存中）
                if use_cache:
                    self.sudo_password = password
                return password
            return None
        except:
            return None
    
    def verify_sudo_password(self, password):
        """验证 sudo 密码是否仍然有效"""
        try:
            # 使用 sudo -v 验证密码
            process = subprocess.Popen(
                ['sudo', '-S', '-v'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            process.communicate(input=password + '\n', timeout=5)
            return process.returncode == 0
        except:
            return False
    
    def resolve_domain_to_ips(self, domain):
        """解析域名到IP地址列表（强制解析真实IP，用于pfctl拦截）"""
        ips = set()
        
        # 方法1: 使用 dig 命令（更可靠）
        try:
            process = subprocess.Popen(
                ['dig', '+short', domain],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=5)
            
            for line in stdout.strip().split('\n'):
                ip = line.strip()
                if ip and ip != '127.0.0.1' and not ip.startswith(';'):
                    # 验证是否是有效的IP地址
                    parts = ip.split('.')
                    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                        ips.add(ip)
        except:
            pass
        
        # 方法2: 如果 dig 失败，使用 nslookup
        if not ips:
            try:
                process = subprocess.Popen(
                    ['nslookup', domain],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(timeout=5)
                
                # 提取IP地址
                for line in stdout.split('\n'):
                    if 'Address:' in line and '127.0.0.1' not in line:
                        ip = line.split('Address:')[-1].strip()
                        if ip and ip != '127.0.0.1':
                            # 验证是否是有效的IP地址
                            parts = ip.split('.')
                            if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                                ips.add(ip)
            except:
                pass
        
        # 方法3: 如果都失败，尝试使用 hosts 文件（但这不是我们想要的，因为我们需要真实IP）
        # 注意：即使 hosts 文件已写入，我们仍然需要解析真实IP来创建pfctl规则
        # 这样才能实时拦截已建立的连接
        
        if not ips:
            print(f"⚠️ 无法解析域名 {domain} 的真实IP地址")
        
        return ips
    
    def setup_pfctl_rules(self, domains):
        """设置 pfctl 防火墙规则（实时拦截）"""
        if not self.use_pfctl:
            return True
        
        try:
            if not self.sudo_password:
                # 尝试获取密码
                password = self.get_sudo_password("需要管理员权限设置防火墙规则", use_cache=True)
                if not password:
                    print("⚠️ 无法获取密码，跳过 pfctl 设置")
                    return False
            
            # 收集所有域名的IP地址（强制解析真实IP）
            all_ips = set()
            failed_domains = []
            
            for domain in domains:
                variants = self.expand_domain_variants(domain)
                domain_ips = set()
                for variant in variants:
                    ips = self.resolve_domain_to_ips(variant)
                    domain_ips.update(ips)
                    all_ips.update(ips)
                    if ips:
                        print(f"域名 {variant} 解析到: {', '.join(ips)}")
                
                # 如果某个域名的所有变体都解析失败，记录
                if not domain_ips:
                    failed_domains.append(domain)
            
            if not all_ips:
                if failed_domains:
                    print(f"⚠️ 以下域名无法解析IP地址，将仅使用 hosts 文件屏蔽: {', '.join(failed_domains)}")
                else:
                    print("⚠️ 所有域名无法解析IP地址，将仅使用 hosts 文件屏蔽")
                # 即使无法解析IP，也返回True，因为hosts文件屏蔽仍然有效
                return True
            
            # 生成 pfctl 规则文件
            rules_content = "# DomainKiller pfctl Rules - Auto Generated\n"
            rules_content += "# Block outbound connections to blocked domains\n\n"
            
            for ip in sorted(all_ips):
                # 阻止所有到这些IP的出站连接
                rules_content += f"block out quick to {ip}\n"
            
            # 写入规则文件
            with open(PFCTL_RULES_FILE, 'w') as f:
                f.write(rules_content)
            
            # 应用 pfctl 规则
            # 首先检查 pfctl 是否已启用
            check_process = subprocess.Popen(
                ['sudo', '-S', 'pfctl', '-s', 'info'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            check_process.communicate(input=self.sudo_password + '\n', timeout=5)
            
            # 如果 pfctl 未启用，先启用它
            if check_process.returncode != 0:
                enable_process = subprocess.Popen(
                    ['sudo', '-S', 'pfctl', '-e'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                enable_process.communicate(input=self.sudo_password + '\n', timeout=5)
            
            # 清除旧规则（如果存在）
            try:
                clear_process = subprocess.Popen(
                    ['sudo', '-S', 'pfctl', '-f', '/dev/null'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                clear_process.communicate(input=self.sudo_password + '\n', timeout=5)
            except:
                pass
            
            # 加载新规则
            load_process = subprocess.Popen(
                ['sudo', '-S', 'pfctl', '-f', PFCTL_RULES_FILE],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = load_process.communicate(input=self.sudo_password + '\n', timeout=10)
            
            if load_process.returncode == 0:
                print(f"✅ pfctl 规则已应用，实时拦截 {len(all_ips)} 个IP地址")
                
                # 验证规则是否生效
                self.verify_pfctl_rules()
                
                return True
            else:
                print(f"⚠️ pfctl 规则应用失败: {stderr}")
                return False
        except Exception as e:
            print(f"⚠️ 设置 pfctl 规则失败: {e}")
            # 即使失败，也不影响 hosts 文件屏蔽
            return False
    
    def verify_pfctl_rules(self):
        """验证 pfctl 规则是否生效"""
        try:
            if not self.sudo_password:
                return False
            
            process = subprocess.Popen(
                ['sudo', '-S', 'pfctl', '-s', 'rules'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=self.sudo_password + '\n', timeout=5)
            
            if process.returncode == 0:
                # 统计 block 规则数量
                block_count = stdout.count('block out quick')
                if block_count > 0:
                    print(f"✅ pfctl 验证: 当前有 {block_count} 条拦截规则生效")
                    return True
                else:
                    print("⚠️ pfctl 验证: 未找到拦截规则")
                    return False
            else:
                print(f"⚠️ pfctl 验证失败: {stderr}")
                return False
        except Exception as e:
            print(f"⚠️ pfctl 验证异常: {e}")
            return False
    
    def remove_pfctl_rules(self):
        """移除 pfctl 防火墙规则"""
        try:
            if not self.sudo_password:
                return True
            
            # 清除所有 pfctl 规则
            process = subprocess.Popen(
                ['sudo', '-S', 'pfctl', '-f', '/dev/null'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            process.communicate(input=self.sudo_password + '\n', timeout=5)
            
            # 删除规则文件
            try:
                if os.path.exists(PFCTL_RULES_FILE):
                    os.unlink(PFCTL_RULES_FILE)
            except:
                pass
            
            print("✅ pfctl 规则已清除")
            return True
        except:
            return False
    
    def check_proxy_server_status(self):
        """检查代理服务器是否正在运行"""
        try:
            # 检查代理服务器实例是否存在
            if not self.proxy_server:
                return False
            
            # 检查线程是否还在运行
            if self.proxy_thread and not self.proxy_thread.is_alive():
                return False
            
            # 尝试连接到代理服务器端口
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_socket.settimeout(0.5)
                result = test_socket.connect_ex(('127.0.0.1', PROXY_PORT))
                test_socket.close()
                return result == 0
            except:
                return False
        except:
            return False
    
    def update_proxy_status_in_window(self):
        """更新窗口中的代理服务器状态"""
        if not self.window:
            return
        
        try:
            is_running = self.check_proxy_server_status()
            if is_running:
                self.proxy_status_label.config(
                    text=f"代理: ✅ 运行中 (端口 {PROXY_PORT})",
                    foreground="green"
                )
            else:
                self.proxy_status_label.config(
                    text="代理: ❌ 未运行",
                    foreground="red"
                )
        except Exception as e:
            print(f"更新代理状态失败: {e}")
    
    def start_proxy_server(self, domains):
        """启动本地 HTTP 代理服务器"""
        if not self.use_proxy:
            if self.window:
                self.window.after(0, lambda: self.update_proxy_status_in_window())
            return False
        
        try:
            # 停止旧代理服务器（如果存在）
            self.stop_proxy_server()
            
            # 更新被屏蔽的域名列表
            BlockingProxyHandler.blocked_domains = set(domains)
            # 添加域名变体
            for domain in domains:
                BlockingProxyHandler.blocked_domains.add(domain)
                BlockingProxyHandler.blocked_domains.add('www.' + domain)
                if domain.startswith('www.'):
                    BlockingProxyHandler.blocked_domains.add(domain[4:])
            
            # 创建代理服务器
            self.proxy_server = HTTPServer(('127.0.0.1', PROXY_PORT), BlockingProxyHandler)
            
            # 在后台线程中运行代理服务器
            def run_proxy():
                try:
                    print(f"✅ 代理服务器已启动在端口 {PROXY_PORT}")
                    if self.window:
                        self.window.after(0, lambda: self.update_proxy_status_in_window())
                    self.proxy_server.serve_forever()
                except Exception as e:
                    print(f"代理服务器错误: {e}")
                    if self.window:
                        self.window.after(0, lambda: self.update_proxy_status_in_window())
            
            self.proxy_thread = threading.Thread(target=run_proxy, daemon=True)
            self.proxy_thread.start()
            
            # 等待服务器启动
            time.sleep(0.5)
            
            # 更新状态显示
            if self.window:
                self.window.after(0, lambda: self.update_proxy_status_in_window())
            
            # 设置系统代理
            result = self.setup_system_proxy()
            
            # 再次更新状态（确保显示最新状态）
            if self.window:
                self.window.after(100, lambda: self.update_proxy_status_in_window())
            
            return result
        except Exception as e:
            print(f"启动代理服务器失败: {e}")
            import traceback
            traceback.print_exc()
            if self.window:
                self.window.after(0, lambda: self.update_proxy_status_in_window())
            return False
    
    def stop_proxy_server(self):
        """停止代理服务器"""
        try:
            if self.proxy_server:
                self.proxy_server.shutdown()
                self.proxy_server = None
            # 清除系统代理设置
            self.clear_system_proxy()
            # 更新状态显示
            if self.window:
                self.window.after(0, lambda: self.update_proxy_status_in_window())
        except:
            pass
    
    def setup_system_proxy(self):
        """设置系统代理（需要管理员权限）"""
        try:
            if not self.sudo_password:
                password = self.get_sudo_password("需要管理员权限设置系统代理", use_cache=True)
                if not password:
                    return False
            
            # 获取当前网络服务名称
            try:
                process = subprocess.Popen(
                    ['networksetup', '-listallnetworkservices'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(timeout=5)
                
                if process.returncode == 0:
                    # 查找第一个活动网络服务（通常是 Wi-Fi 或 Ethernet）
                    lines = stdout.strip().split('\n')[1:]  # 跳过第一行标题
                    active_service = None
                    for line in lines:
                        service = line.strip()
                        if service and not service.startswith('*'):
                            active_service = service
                            break
                    
                    if active_service:
                        # 设置 HTTP 代理
                        http_proxy_cmd = [
                            'sudo', '-S', 'networksetup', '-setwebproxy',
                            active_service, '127.0.0.1', str(PROXY_PORT)
                        ]
                        process = subprocess.Popen(
                            http_proxy_cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        process.communicate(input=self.sudo_password + '\n', timeout=5)
                        
                        # 设置 HTTPS 代理
                        https_proxy_cmd = [
                            'sudo', '-S', 'networksetup', '-setsecurewebproxy',
                            active_service, '127.0.0.1', str(PROXY_PORT)
                        ]
                        process = subprocess.Popen(
                            https_proxy_cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        process.communicate(input=self.sudo_password + '\n', timeout=5)
                        
                        # 启用代理
                        enable_cmd = [
                            'sudo', '-S', 'networksetup', '-setwebproxystate',
                            active_service, 'on'
                        ]
                        process = subprocess.Popen(
                            enable_cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        process.communicate(input=self.sudo_password + '\n', timeout=5)
                        
                        enable_https_cmd = [
                            'sudo', '-S', 'networksetup', '-setsecurewebproxystate',
                            active_service, 'on'
                        ]
                        process = subprocess.Popen(
                            enable_https_cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        process.communicate(input=self.sudo_password + '\n', timeout=5)
                        
                        print(f"✅ 系统代理已设置: {active_service} -> 127.0.0.1:{PROXY_PORT}")
                        return True
            except Exception as e:
                print(f"设置系统代理失败: {e}")
                return False
        except Exception as e:
            print(f"设置系统代理异常: {e}")
            return False
    
    def clear_system_proxy(self):
        """清除系统代理设置"""
        try:
            if not self.sudo_password:
                return
            
            # 获取当前网络服务名称
            try:
                process = subprocess.Popen(
                    ['networksetup', '-listallnetworkservices'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(timeout=5)
                
                if process.returncode == 0:
                    lines = stdout.strip().split('\n')[1:]
                    for line in lines:
                        service = line.strip()
                        if service and not service.startswith('*'):
                            # 禁用代理
                            try:
                                disable_cmd = [
                                    'sudo', '-S', 'networksetup', '-setwebproxystate',
                                    service, 'off'
                                ]
                                process = subprocess.Popen(
                                    disable_cmd,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True
                                )
                                process.communicate(input=self.sudo_password + '\n', timeout=5)
                                
                                disable_https_cmd = [
                                    'sudo', '-S', 'networksetup', '-setsecurewebproxystate',
                                    service, 'off'
                                ]
                                process = subprocess.Popen(
                                    disable_https_cmd,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True
                                )
                                process.communicate(input=self.sudo_password + '\n', timeout=5)
                            except:
                                pass
            except:
                pass
        except:
            pass
    
    def flush_dns_cache(self):
        """刷新 DNS 缓存（macOS）- 强制刷新（增强版，支持 Safari）"""
        try:
            if not self.sudo_password:
                return
            
            print("🔄 正在强制刷新 DNS 缓存（包括 Safari）...")
            
            # macOS 不同版本使用不同的命令（按顺序执行，确保刷新）
            # 增强版：添加更多刷新命令，确保 Safari 也能生效
            commands = [
                # 1. 刷新系统 DNS 缓存
                ['sudo', '-S', 'dscacheutil', '-flushcache'],
                
                # 2. 重启 mDNSResponder（macOS 的 DNS 服务）
                ['sudo', '-S', 'killall', '-HUP', 'mDNSResponder'],
                
                # 3. 重启 mDNSResponderHelper
                ['sudo', '-S', 'killall', 'mDNSResponderHelper'],
                
                # 4. 完全重启 mDNSResponder（更彻底）
                ['sudo', '-S', 'killall', 'mDNSResponder'],
            ]
            
            # 执行基础刷新命令
            for cmd in commands:
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = process.communicate(input=self.sudo_password + '\n', timeout=5)
                    # killall 命令如果找不到进程会返回非零，这是正常的
                    if process.returncode != 0 and 'killall' not in cmd[1]:
                        print(f"⚠️ DNS 刷新命令执行警告: {cmd[1]} - {stderr}")
                except Exception as e:
                    # 某些命令可能在某些系统上不存在，忽略错误
                    pass
            
            # 5. 使用 launchctl 重启 mDNSResponder（更可靠）
            try:
                process = subprocess.Popen(
                    ['sudo', '-S', 'launchctl', 'kickstart', '-k', 'system/com.apple.mDNSResponder'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                process.communicate(input=self.sudo_password + '\n', timeout=5)
            except:
                pass
            
            # 6. 刷新网络配置缓存（某些 macOS 版本需要，特别是 Safari）
            # 获取当前网络接口
            try:
                # 尝试刷新 Wi-Fi 和 Ethernet 的 DNS 设置（这会触发 DNS 刷新）
                network_commands = [
                    ['sudo', '-S', 'networksetup', '-setdnsservers', 'Wi-Fi', 'Empty'],
                    ['sudo', '-S', 'networksetup', '-setdnsservers', 'Ethernet', 'Empty'],
                ]
                
                for cmd in network_commands:
                    try:
                        process = subprocess.Popen(
                            cmd,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        process.communicate(input=self.sudo_password + '\n', timeout=5)
                    except:
                        # 某些接口可能不存在，忽略错误
                        pass
            except:
                pass
            
            # 额外等待，确保 DNS 刷新完成（Safari 需要更长时间）
            time.sleep(1.0)
            
            print("✅ DNS 缓存已强制刷新（包括 Safari）")
        except Exception as e:
            print(f"⚠️ DNS 刷新过程出错: {e}")
    
    def write_hosts_file(self, content):
        """写入 hosts 文件（使用更稳定的方法）"""
        try:
            # 尝试直接写入
            with open(HOSTS_PATH, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            # 刷新 DNS 缓存
            self.flush_dns_cache()
            return True
        except PermissionError:
            # 需要 sudo，使用缓存的密码
            password = self.get_sudo_password("需要管理员权限写入 hosts 文件", use_cache=True)
            if not password:
                return False
            
            # 使用临时文件 + sudo mv（更稳定可靠）
            import tempfile
            temp_path = None
            try:
                # 创建临时文件
                temp_fd, temp_path = tempfile.mkstemp(text=True)
                with os.fdopen(temp_fd, 'w', encoding='utf-8', newline='\n') as temp_file:
                    temp_file.write(content)
                
                # 使用 sudo mv 移动文件（原子操作，更可靠）
                process = subprocess.Popen(
                    ['sudo', '-S', 'mv', temp_path, HOSTS_PATH],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=password + '\n', timeout=10)
                
                if process.returncode == 0:
                    # 等待文件系统同步
                    time.sleep(0.2)
                    
                    # 刷新 DNS 缓存
                    self.flush_dns_cache()
                    
                    # 严格验证写入是否成功
                    try:
                        verify_content = self.read_hosts_file(silent=True)
                        if verify_content:
                            # 检查标记是否存在
                            if MARKER_START not in verify_content or MARKER_END not in verify_content:
                                print("⚠️ 警告: hosts 文件中未找到标记")
                                return False
                            
                            # 提取写入的域名行
                            in_block = False
                            written_domains = set()
                            for line in verify_content.split('\n'):
                                if MARKER_START in line:
                                    in_block = True
                                    continue
                                if MARKER_END in line:
                                    in_block = False
                                    continue
                                if in_block and LOCALHOST_IP in line:
                                    # 提取域名（格式: 127.0.0.1 domain）
                                    parts = line.strip().split()
                                    if len(parts) >= 2 and parts[0] == LOCALHOST_IP:
                                        written_domains.add(parts[1].strip())
                            
                            # 提取应该写入的域名
                            expected_domains = set()
                            in_block = False
                            for line in content.split('\n'):
                                if MARKER_START in line:
                                    in_block = True
                                    continue
                                if MARKER_END in line:
                                    in_block = False
                                    continue
                                if in_block and LOCALHOST_IP in line:
                                    parts = line.strip().split()
                                    if len(parts) >= 2 and parts[0] == LOCALHOST_IP:
                                        expected_domains.add(parts[1].strip())
                            
                            # 检查所有域名是否都已写入
                            missing = expected_domains - written_domains
                            if missing:
                                print(f"⚠️ 警告: 以下域名未成功写入 hosts 文件: {', '.join(missing)}")
                                print(f"已写入的域名: {len(written_domains)}, 期望的域名: {len(expected_domains)}")
                                return False
                            
                            print(f"✅ 成功写入 {len(written_domains)} 个域名到 hosts 文件")
                            return True
                    except Exception as e:
                        print(f"⚠️ 验证写入时出错: {e}")
                        # 即使验证失败，如果 mv 成功，也认为写入成功（但会记录警告）
                        return True
                
                # 如果失败，清除缓存的密码
                if process.returncode != 0:
                    self.sudo_password = None
                    print(f"写入失败: {stderr}")
                return False
            except Exception as e:
                print(f"写入 hosts 文件异常: {e}")
                # 清理临时文件
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                self.sudo_password = None
                return False
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
    
    def expand_domain_variants(self, domain):
        """扩展域名变体（主域名和 www 子域名）"""
        variants = set()
        domain = domain.strip().lower()
        
        if not domain:
            return variants
        
        # 添加原始域名
        variants.add(domain)
        
        # 如果有 www 前缀，也添加不带 www 的版本
        if domain.startswith('www.'):
            variants.add(domain[4:])  # 移除 www.
        else:
            # 如果没有 www 前缀，也添加带 www 的版本
            variants.add(f"www.{domain}")
        
        return variants
    
    def add_block_rules(self, hosts_content, domains):
        """添加屏蔽规则到 hosts 文件（增强版：包含域名变体）"""
        content = self.remove_old_rules(hosts_content)
        
        if domains:
            content += f"\n\n{MARKER_START}\n"
            all_variants = set()
            
            # 为每个域名生成所有变体
            for domain in domains:
                variants = self.expand_domain_variants(domain)
                all_variants.update(variants)
                print(f"域名 {domain} 扩展为: {', '.join(variants)}")
            
            # 按字母顺序排序并写入
            for domain in sorted(all_variants):
                content += f"{LOCALHOST_IP} {domain}\n"
            
            content += f"{MARKER_END}\n"
            print(f"准备写入 {len(all_variants)} 个域名变体到 hosts 文件")
        
        return content
    
    def verify_domain_blocked(self, domain):
        """验证域名是否真的被屏蔽（通过 ping 测试）"""
        try:
            # 使用 ping 测试域名解析
            process = subprocess.Popen(
                ['ping', '-c', '1', '-W', '1000', domain],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=2)
            # 如果 ping 返回 127.0.0.1，说明屏蔽成功
            if '127.0.0.1' in stdout or '127.0.0.1' in stderr:
                return True
            return False
        except:
            return False
    
    def block_domains(self, domains):
        """屏蔽域名（三重保护：hosts文件 + pfctl实时拦截 + 代理服务器）"""
        if not domains:
            return self.restore_hosts()
        
        try:
            # 1. 使用 hosts 文件屏蔽（基础屏蔽）
            hosts_content = self.read_hosts_file(silent=True)
            if not hosts_content and not self.sudo_password:
                hosts_content = self.read_hosts_file(silent=False)
            
            new_content = self.add_block_rules(hosts_content, domains)
            hosts_result = self.write_hosts_file(new_content)
            
            # 2. 使用 pfctl 防火墙实时拦截（强制断开已建立的连接）
            pfctl_result = self.setup_pfctl_rules(domains)
            
            # 3. 启动代理服务器（对 Safari 更有效）
            proxy_result = self.start_proxy_server(domains)
            
            if hosts_result:
                # 强制刷新 DNS 缓存
                self.flush_dns_cache()
                
                # 验证写入是否成功（检查所有域名变体）
                try:
                    verify_content = self.read_hosts_file(silent=True)
                    if verify_content:
                        # 检查是否包含所有域名及其变体
                        all_found = True
                        missing_domains = []
                        
                        for domain in domains:
                            variants = self.expand_domain_variants(domain)
                            found_any = False
                            for variant in variants:
                                # 检查 hosts 文件中是否有这个域名
                                if f"{LOCALHOST_IP} {variant}" in verify_content:
                                    found_any = True
                                    # 可选：通过 ping 验证（可能较慢，注释掉）
                                    # if self.verify_domain_blocked(variant):
                                    #     print(f"✓ {variant} 已成功屏蔽")
                                    break
                            if not found_any:
                                all_found = False
                                missing_domains.append(domain)
                        
                        if all_found:
                            self.current_domains = set(domains)
                            if self.window:
                                self.update_window_domains()
                            
                            # 显示屏蔽方式
                            methods = []
                            if hosts_result:
                                methods.append("hosts文件")
                            if pfctl_result:
                                methods.append("pfctl防火墙(实时拦截)")
                            if proxy_result:
                                methods.append("代理服务器(Safari专用)")
                            
                            print(f"✅ 成功屏蔽 {len(domains)} 个域名（方式: {', '.join(methods)}）")
                            print("💡 提示: pfctl 防火墙可以实时拦截已打开的网站连接")
                            print("💡 提示: 代理服务器可以拦截 Safari 浏览器的请求")
                            if not proxy_result:
                                print("💡 Safari 用户: 如果仍能访问，请重启 Safari 浏览器（完全退出并重新打开）")
                            return True
                        else:
                            print(f"⚠️ 警告: 以下域名可能未成功屏蔽: {', '.join(missing_domains)}")
                            print(f"当前 hosts 文件内容片段:\n{verify_content[-500:]}")
                            # 即使部分失败，也更新当前域名列表
                            self.current_domains = set(domains)
                            if self.window:
                                self.update_window_domains()
                            return True
                except Exception as e:
                    print(f"验证写入失败: {e}")
                
                # 如果验证失败，但写入返回成功，仍然更新
                self.current_domains = set(domains)
                if self.window:
                    self.update_window_domains()
                return True
            
            return False
        except Exception as e:
            print(f"屏蔽域名失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def restore_hosts(self):
        """恢复 hosts 文件并清除所有规则"""
        try:
            # 1. 停止代理服务器
            self.stop_proxy_server()
            
            # 2. 清除 pfctl 规则
            self.remove_pfctl_rules()
            
            # 3. 恢复 hosts 文件
            hosts_content = self.read_hosts_file()
            new_content = self.remove_old_rules(hosts_content)
            result = self.write_hosts_file(new_content)
            
            if result:
                self.flush_dns_cache()
            
            return result
        except Exception as e:
            print(f"恢复失败: {e}")
            return False
    
    def sync_and_block(self):
        """同步域名并屏蔽（立即执行，不等待）"""
        try:
            # 步骤1: 从 API 获取最新域名（强制刷新）
            if self.window:
                self.window.after(0, lambda: self.update_status_in_window("🔄 正在从 API 刷新域名列表..."))
            
            print("=" * 30)
            print("开始从 API 同步域名...")
            api_result = self.fetch_domains_from_api()
            
            if api_result:
                # API 调用成功
                api_domains, api_password = api_result
                if api_password:
                    self.password = api_password
                    print(f"✓ 从 API 获取到密码")
                
                print(f"✓ 从 API 获取到 {len(api_domains)} 个域名")
                print(f"域名列表: {', '.join(sorted(api_domains)[:10])}{'...' if len(api_domains) > 10 else ''}")
                
                # 更新本地文件（API 域名会写入本地文件，但保留原有本地域名）
                # 注意：这里不覆盖本地文件，只保存 API 域名到内存
                self.api_domains = set(api_domains)  # 保存 API 同步的域名
                
                # 合并 API 和本地域名进行屏蔽
                local_domains = self.read_domains_file()
                self.current_domains = self.api_domains | local_domains
                
                if self.window:
                    self.window.after(0, lambda: self.update_status_in_window(f"✓ 已获取 {len(api_domains)} 个 API 域名，合并后共 {len(self.current_domains)} 个域名，正在屏蔽..."))
                    # 立即更新窗口列表
                    self.window.after(0, lambda: self.update_window_domains())
            else:
                # API 失败，从本地文件读取
                print("API 调用失败，从本地文件读取域名")
                local_domains = self.read_domains_file()
                self.api_domains = set()  # API 失败，清空 API 列表
                self.current_domains = local_domains  # 只使用本地域名
                
                if self.window:
                    if self.current_domains:
                        self.window.after(0, lambda: self.update_status_in_window(f"使用本地缓存 {len(self.current_domains)} 个域名，正在屏蔽..."))
                    else:
                        self.window.after(0, lambda: self.update_status_in_window("未找到域名列表", error=True))
                    # 更新窗口列表
                    self.window.after(0, lambda: self.update_window_domains())
            
            # 步骤2: 立即屏蔽域名（合并 API + 本地）
            # 确保合并最新的 API 和本地域名
            local_domains = self.read_domains_file()
            all_domains = self.api_domains | local_domains
            self.current_domains = all_domains
            
            if self.current_domains:
                print("=" * 30)
                print(f"开始屏蔽 {len(self.current_domains)} 个域名（API: {len(self.api_domains)}, 本地: {len(local_domains)}）...")
                if self.window:
                    self.window.after(0, lambda: self.update_status_in_window(f"🛡️ 正在屏蔽 {len(self.current_domains)} 个域名（API+本地）..."))
                success = self.block_domains(self.current_domains)
                
                if success:
                    print(f"✅ 成功屏蔽 {len(self.current_domains)} 个域名")
                    print("=" * 30)
                    if self.window:
                        self.window.after(0, lambda: self.update_status_in_window(f"✅ 已同步并屏蔽 {len(self.current_domains)} 个域名"))
                        # 立即刷新列表（确保显示最新数据）
                        self.window.after(0, lambda: self.update_window_domains())
                else:
                    print("❌ 屏蔽域名失败")
                    if self.window:
                        self.window.after(0, lambda: self.update_status_in_window("❌ 屏蔽域名失败，请检查权限", error=True))
                        # 即使失败也刷新列表
                        self.window.after(100, lambda: self.update_window_domains())
            else:
                # 没有域名，清除屏蔽规则
                print("没有域名需要屏蔽，清除屏蔽规则...")
                self.api_domains = set()  # 清空 API 列表
                success = self.restore_hosts()
                if success and self.window:
                    self.window.after(0, lambda: self.update_status_in_window("当前没有需要屏蔽的域名"))
                    self.window.after(0, lambda: self.update_window_domains())
        except Exception as e:
            error_msg = f"同步失败: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            if self.window:
                self.window.after(0, lambda: self.update_status_in_window(f"❌ {error_msg}", error=True))
    
    def check_and_update(self):
        """定时检查并更新"""
        while self.running:
            try:
                self.sync_and_block()
            except Exception as e:
                print(f"检查更新失败: {e}")
            
            for _ in range(CHECK_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)
    
    def create_window(self):
        """创建显示窗口（优化启动速度）"""
        if self.window:
            return
        
        try:
            self.window = tk.Tk()
            self.window.title("网站访问控制")
            self.window.geometry("800x600")
            
            # 状态栏
            status_frame = ttk.Frame(self.window, padding="10")
            status_frame.pack(fill=tk.X, padx=5, pady=5)
            
            self.status_label = ttk.Label(status_frame, text="状态: 正在启动...")
            self.status_label.pack(side=tk.LEFT)
            
            # 代理服务器状态标签
            self.proxy_status_label = ttk.Label(status_frame, text="代理: 检查中...", foreground="gray")
            self.proxy_status_label.pack(side=tk.LEFT, padx=(20, 0))
            
            self.count_label = ttk.Label(status_frame, text="", foreground="blue")
            self.count_label.pack(side=tk.RIGHT)
            
            # 按钮
            button_frame = ttk.Frame(self.window, padding="5")
            button_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Button(button_frame, text="立即同步", 
                      command=lambda: threading.Thread(target=self.sync_and_block, daemon=True).start()).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="刷新列表", 
                      command=self.update_window_domains).pack(side=tk.LEFT, padx=5)
            
            # 域名列表 - 分成两个框
            list_frame = ttk.Frame(self.window, padding="5")
            list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 左侧：API 同步的域名（只读）
            api_frame = ttk.LabelFrame(list_frame, text="🔄 API 域名（只读）", padding="5")
            api_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            self.api_domains_text = scrolledtext.ScrolledText(api_frame, wrap=tk.WORD, font=("Consolas", 9), 
                                                               state=tk.DISABLED, bg="#e8f5e9", height=12)
            self.api_domains_text.pack(fill=tk.BOTH, expand=True)
            
            self.api_count_label = ttk.Label(api_frame, text="0 个域名", foreground="green")
            self.api_count_label.pack(anchor=tk.W, pady=(5, 0))
            
            # 右侧：本地文件域名（可编辑）
            local_frame = ttk.LabelFrame(list_frame, text="📁 本地域名（可编辑）", padding="5")
            local_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
            
            self.local_domains_text = scrolledtext.ScrolledText(local_frame, wrap=tk.WORD, font=("Consolas", 9), 
                                                                 state=tk.DISABLED, bg="#fff3e0", height=12)
            self.local_domains_text.pack(fill=tk.BOTH, expand=True)
            
            # 本地域名框下方的按钮
            local_button_frame = ttk.Frame(local_frame)
            local_button_frame.pack(fill=tk.X, pady=(5, 0))
            
            self.local_count_label = ttk.Label(local_button_frame, text="0 个域名", foreground="orange")
            self.local_count_label.pack(side=tk.LEFT, anchor=tk.W)
            
            ttk.Button(local_button_frame, text="✏️ 编辑", 
                      command=self.on_edit_local_domains).pack(side=tk.RIGHT, padx=(5, 0))
            
            # 密码输入
            password_frame = ttk.Frame(self.window, padding="5")
            password_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
            
            password_left = ttk.Frame(password_frame)
            password_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            ttk.Label(password_left, text="密码:").pack(side=tk.LEFT, padx=(0, 5))
            self.password_entry = ttk.Entry(password_left, show='*', width=20)
            self.password_entry.pack(side=tk.LEFT, padx=5)
            
            ttk.Button(password_left, text="恢复访问", command=self.on_restore).pack(side=tk.LEFT, padx=5)
            ttk.Button(password_left, text="退出程序", command=self.on_quit).pack(side=tk.LEFT, padx=5)
            
            # 窗口关闭
            self.window.protocol("WM_DELETE_WINDOW", lambda: self.window.withdraw())
            
            # 立即显示初始列表（从内存或文件）
            self.update_window_domains()
            
            # 立即检查代理服务器状态
            self.update_proxy_status_in_window()
            
            # 定期检查代理服务器状态（每3秒检查一次）
            def periodic_check_proxy():
                if self.window and self.running:
                    self.update_proxy_status_in_window()
                    self.window.after(3000, periodic_check_proxy)
            
            self.window.after(1000, periodic_check_proxy)  # 1秒后开始第一次检查
        except Exception as e:
            print(f"创建窗口失败: {e}")
            import traceback
            traceback.print_exc()
    
    def update_window_domains(self):
        """更新窗口中的域名列表（分为 API 和本地两个框）"""
        if not self.window:
            return
        
        try:
            # 更新 API 同步的域名列表（当前正在屏蔽的）
            self.api_domains_text.config(state=tk.NORMAL)
            self.api_domains_text.delete(1.0, tk.END)
            
            if self.api_domains:
                sorted_api_domains = sorted(self.api_domains)
                for i, domain in enumerate(sorted_api_domains, 1):
                    self.api_domains_text.insert(tk.END, f"{i}. {domain}\n")
                self.api_count_label.config(text=f"✅ {len(self.api_domains)} 个域名（正在屏蔽）")
                print(f"✅ API 列表已更新，显示 {len(self.api_domains)} 个域名")
            else:
                self.api_domains_text.insert(tk.END, "暂无 API 同步的域名\n")
                self.api_count_label.config(text="0 个域名")
                print("⚠️ API 列表为空")
            
            self.api_domains_text.config(state=tk.DISABLED)
            
            # 更新本地文件的域名列表
            local_domains = self.read_domains_file()
            self.local_domains_text.config(state=tk.NORMAL)
            self.local_domains_text.delete(1.0, tk.END)
            
            if local_domains:
                sorted_local_domains = sorted(local_domains)
                for i, domain in enumerate(sorted_local_domains, 1):
                    self.local_domains_text.insert(tk.END, f"{i}. {domain}\n")
                self.local_count_label.config(text=f"📁 {len(local_domains)} 个域名（本地文件）")
                print(f"✅ 本地列表已更新，显示 {len(local_domains)} 个域名")
            else:
                self.local_domains_text.insert(tk.END, "本地文件暂无域名\n")
                self.local_count_label.config(text="0 个域名")
                print("⚠️ 本地列表为空")
            
            self.local_domains_text.config(state=tk.DISABLED)
            
            # 更新总计数（API + 本地）
            local_domains = self.read_domains_file()
            total_count = len(self.api_domains | local_domains)
            self.count_label.config(text=f"共屏蔽 {total_count} 个域名（API: {len(self.api_domains)}, 本地: {len(local_domains)}）" if total_count > 0 else "")
            
        except Exception as e:
            print(f"❌ 更新窗口失败: {e}")
            import traceback
            traceback.print_exc()
    
    def update_status_in_window(self, message, error=False):
        """更新窗口状态栏"""
        if not self.window:
            return
        
        try:
            color = "red" if error else "green"
            self.status_label.config(text=f"状态: {message}", foreground=color)
        except:
            pass
    
    def verify_password(self, input_password):
        """验证密码"""
        try:
            api_result = self.fetch_domains_from_api()
            if api_result:
                _, api_password = api_result
                return api_password and input_password == api_password
            return False
        except:
            return False
    
    def on_edit_local_domains(self):
        """编辑本地域名文件（需要密码验证）"""
        password = self.password_entry.get()
        if not password:
            messagebox.showwarning("警告", "请输入密码以编辑本地域名文件！")
            return
        
        if not self.verify_password(password):
            messagebox.showerror("错误", "密码错误")
            self.password_entry.delete(0, tk.END)
            return
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.window)
        edit_window.title("编辑本地域名")
        edit_window.geometry("500x400")
        
        # 读取当前本地域名
        local_domains = self.read_domains_file()
        domains_text = "\n".join(sorted(local_domains)) if local_domains else ""
        
        # 说明文字
        info_label = ttk.Label(edit_window, text="每行一个域名，修改后点击保存", foreground="gray")
        info_label.pack(pady=5)
        
        # 文本编辑框
        text_frame = ttk.Frame(edit_window, padding="5")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        text_editor = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Consolas", 10))
        text_editor.pack(fill=tk.BOTH, expand=True)
        text_editor.insert(1.0, domains_text)
        
        # 按钮
        button_frame = ttk.Frame(edit_window, padding="5")
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        def save_domains():
            """保存域名"""
            content = text_editor.get(1.0, tk.END).strip()
            domains = set()
            
            for line in content.split('\n'):
                domain = line.strip()
                if domain and not domain.startswith('#'):
                    # 清理域名（去除协议前缀）
                    if domain.startswith("http://"):
                        domain = domain[7:]
                    elif domain.startswith("https://"):
                        domain = domain[8:]
                    if "/" in domain:
                        domain = domain.split("/")[0]
                    domain = domain.rstrip("/").strip()
                    if domain:
                        domains.add(domain)
            
            # 保存到文件
            try:
                # 确保目录存在
                self.domains_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 保存文件
                file_path = str(self.domains_file)
                print(f"正在保存域名到文件: {file_path}")
                print(f"目录是否存在: {self.domains_file.parent.exists()}")
                print(f"目录可写: {os.access(self.domains_file.parent, os.W_OK)}")
                
                # 确保目录存在
                try:
                    self.domains_file.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"创建目录失败: {e}")
                
                # 写入文件
                try:
                    with open(self.domains_file, 'w', encoding='utf-8') as f:
                        for domain in sorted(domains):
                            f.write(f"{domain}\n")
                        # 强制刷新
                        try:
                            f.flush()
                            os.fsync(f.fileno())
                        except:
                            pass
                except Exception as e:
                    print(f"❌ 写入文件失败: {e}")
                    messagebox.showerror("错误", f"保存文件失败: {e}\n文件路径: {file_path}")
                    return
                
                # 验证文件是否写入成功
                time.sleep(0.1)  # 等待文件系统同步
                
                if self.domains_file.exists():
                    file_size = self.domains_file.stat().st_size
                    print(f"✅ 文件保存成功: {file_path}, 大小: {file_size} 字节")
                    # 读取验证
                    with open(self.domains_file, 'r', encoding='utf-8') as f:
                        saved_count = len([l for l in f if l.strip()])
                    print(f"✅ 文件验证: 保存了 {saved_count} 个域名")
                    messagebox.showinfo("成功", f"已保存 {len(domains)} 个域名到本地文件\n文件路径: {file_path}\n文件大小: {file_size} 字节")
                else:
                    print(f"❌ 文件保存失败: {file_path} 不存在")
                    messagebox.showerror("错误", f"文件保存失败: {file_path} 不存在\n请检查文件路径和权限")
                    return
                
                edit_window.destroy()
                
                # 重新屏蔽（合并 API + 新的本地域名）
                local_domains = self.read_domains_file()
                all_domains = self.api_domains | local_domains
                self.current_domains = all_domains
                
                if all_domains:
                    threading.Thread(target=lambda: self.block_domains(all_domains), daemon=True).start()
                    self.update_status_in_window(f"✅ 已更新本地域名，重新屏蔽 {len(all_domains)} 个域名（API+本地）")
                else:
                    self.restore_hosts()
                    self.update_status_in_window("已清空所有域名")
                
                self.update_window_domains()
                self.password_entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
        
        ttk.Button(button_frame, text="保存", command=save_domains).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=edit_window.destroy).pack(side=tk.RIGHT)
    
    def on_restore(self):
        """恢复访问"""
        password = self.password_entry.get()
        if not password:
            messagebox.showwarning("警告", "请输入密码！")
            return
        
        if self.verify_password(password):
            if self.restore_hosts():
                self.current_domains = set()
                self.api_domains = set()
                self.update_window_domains()
                self.update_status_in_window("已恢复所有网站访问")
                self.password_entry.delete(0, tk.END)
            else:
                messagebox.showerror("错误", "恢复访问失败")
        else:
            messagebox.showerror("错误", "密码错误")
            self.password_entry.delete(0, tk.END)
    
    def on_quit(self):
        """退出程序"""
        password = self.password_entry.get()
        if not password:
            messagebox.showwarning("警告", "请输入密码！")
            return
        
        if self.verify_password(password):
            self.restore_hosts()
            self.running = False
            if self.window:
                self.window.quit()
                self.window.destroy()
        else:
            messagebox.showerror("错误", "密码错误")
            self.password_entry.delete(0, tk.END)
    
    def run(self):
        """运行主程序"""
        try:
            # 立即创建并显示窗口（在主线程，不等待任何操作）
            self.create_window()
            if not self.window:
                print("无法创建窗口")
                return
            
            # 立即显示窗口（不等待后台任务）
            self.window.update_idletasks()
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
            
            # 启动后台线程（窗口已显示，后台任务不阻塞）
            self.running = True
            
            # 在后台线程中：先获取密码，然后立即同步并屏蔽
            def startup_and_sync():
                try:
                    print("=" * 50)
                    print("程序启动，开始初始化...")
                    print("=" * 50)
                    
                    # 1. 明确获取 sudo 密码（启动时必须输入）
                    if self.window:
                        self.window.after(0, lambda: self.update_status_in_window("🔐 需要管理员权限，请在弹出的对话框中输入密码..."))
                    
                    print("步骤 1/3: 获取管理员权限...")
                    print("提示：即将弹出密码输入对话框，请输入您的 macOS 管理员密码")
                    
                    # 明确获取密码（使用明确的提示信息）
                    password = self.get_sudo_password("程序需要管理员权限来修改 hosts 文件和设置防火墙规则", use_cache=False)
                    if password:
                        self.sudo_password = password
                        print("✓ 密码已获取并缓存")
                        if self.window:
                            self.window.after(0, lambda: self.update_status_in_window("✓ 权限获取成功，正在刷新 API 列表..."))
                    else:
                        print("⚠️ 未获取到密码，将在后续操作中提示")
                        if self.window:
                            self.window.after(0, lambda: self.update_status_in_window("⚠️ 未获取到密码，将在需要时提示", error=True))
                    
                    # 2. 立即同步并屏蔽（不等待用户操作）
                    print("步骤 2/3: 从 API 刷新域名列表并屏蔽...")
                    if self.window:
                        self.window.after(0, lambda: self.update_status_in_window("🔄 正在从服务器获取最新域名列表..."))
                    self.sync_and_block()
                    
                    # 确保列表已刷新（同步完成后立即更新）
                    if self.window:
                        # 立即刷新（使用同步后的内存数据）
                        self.window.after(0, lambda: self.update_window_domains())
                        # 延迟刷新一次（确保文件已写入，作为备份）
                        self.window.after(500, lambda: self.update_window_domains())
                    
                    # 3. 启动定时检查（在单独的线程中）
                    print("步骤 3/3: 启动定时检查...")
                    threading.Thread(target=self.check_and_update, daemon=True).start()
                    print("✅ 初始化完成")
                    print("=" * 50)
                except Exception as e:
                    error_msg = f"启动时处理失败: {e}"
                    print(f"❌ {error_msg}")
                    import traceback
                    traceback.print_exc()
                    if self.window:
                        self.window.after(0, lambda: self.update_status_in_window(f"❌ 启动错误: {e}", error=True))
            
            # 启动后台处理（立即执行，不延迟）
            threading.Thread(target=startup_and_sync, daemon=True).start()
            
            # 运行主循环（不阻塞）
            self.window.mainloop()
        except Exception as e:
            print(f"运行程序失败: {e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    try:
        if sys.platform != 'darwin':
            print("此程序仅支持 macOS 系统")
            return
        
        killer = DomainKiller()
        killer.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序发生错误: {e}")
        import traceback
        traceback.print_exc()
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("程序错误", f"程序发生错误:\n{e}")
            root.destroy()
        except:
            pass


if __name__ == "__main__":
    main()

