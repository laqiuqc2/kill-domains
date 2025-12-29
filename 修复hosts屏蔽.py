#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 hosts 文件屏蔽 - 手动检查和修复工具
"""

import subprocess
import sys

HOSTS_PATH = "/etc/hosts"
LOCALHOST_IP = "127.0.0.1"
MARKER_START = "# === Kill Domains Start ==="
MARKER_END = "# === Kill Domains End ==="

def read_hosts_file():
    """读取 hosts 文件"""
    try:
        process = subprocess.Popen(
            ['sudo', 'cat', HOSTS_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            return stdout
        else:
            print(f"读取 hosts 文件失败: {stderr}")
            return None
    except Exception as e:
        print(f"读取 hosts 文件异常: {e}")
        return None

def check_domain(domain):
    """检查域名是否在 hosts 文件中"""
    content = read_hosts_file()
    if not content:
        return False
    
    # 检查主域名和 www 变体
    variants = [domain, f"www.{domain}"]
    if domain.startswith('www.'):
        variants.append(domain[4:])
    
    found = []
    for variant in variants:
        if f"{LOCALHOST_IP} {variant}" in content:
            found.append(variant)
    
    return found

def main():
    print("=" * 50)
    print("Hosts 文件屏蔽检查工具")
    print("=" * 50)
    print()
    
    # 检查特定域名
    test_domains = ['le.com', 'youku.com']
    
    for domain in test_domains:
        print(f"检查域名: {domain}")
        found = check_domain(domain)
        if found:
            print(f"  ✅ 找到以下变体: {', '.join(found)}")
        else:
            print(f"  ❌ 未找到任何变体")
        print()
    
    # 显示 hosts 文件中的屏蔽规则
    print("=" * 50)
    print("当前 hosts 文件中的屏蔽规则:")
    print("=" * 50)
    
    content = read_hosts_file()
    if content:
        in_block = False
        domain_count = 0
        for line in content.split('\n'):
            if MARKER_START in line:
                in_block = True
                print(line)
                continue
            if MARKER_END in line:
                in_block = False
                print(line)
                break
            if in_block:
                if LOCALHOST_IP in line:
                    domain_count += 1
                    print(line)
        
        print(f"\n总共找到 {domain_count} 个屏蔽规则")
    else:
        print("无法读取 hosts 文件")
    
    print()
    print("=" * 50)
    print("提示:")
    print("=" * 50)
    print("1. 如果域名未在 hosts 文件中，请运行程序重新同步")
    print("2. 如果域名已在 hosts 文件中但仍能访问，请:")
    print("   - 清除浏览器缓存")
    print("   - 重启浏览器")
    print("   - 使用隐私模式测试")
    print("   - 运行: sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder")

if __name__ == '__main__':
    main()

