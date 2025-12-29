#!/bin/bash
# 检查 hosts 文件中是否包含指定域名

echo "=========================================="
echo "检查 hosts 文件中的屏蔽规则"
echo "=========================================="
echo ""

# 读取 hosts 文件
echo "当前 hosts 文件内容（屏蔽规则部分）:"
echo "----------------------------------------"
sudo cat /etc/hosts | grep -A 1000 "Kill Domains Start" | grep -B 1000 "Kill Domains End" || echo "未找到屏蔽规则"
echo ""

# 检查特定域名
echo "检查 le.com 相关域名:"
echo "----------------------------------------"
sudo cat /etc/hosts | grep "le.com" || echo "未找到 le.com"
echo ""

echo "检查 youku.com 相关域名:"
echo "----------------------------------------"
sudo cat /etc/hosts | grep "qq.com" || echo "未找到 qq.com"
echo ""

echo "=========================================="
echo "DNS 缓存状态:"
echo "=========================================="
echo "提示: 如果域名已在 hosts 文件中，但仍能访问，可能是："
echo "1. 浏览器缓存 - 请清除浏览器缓存或使用隐私模式"
echo "2. DNS 缓存 - 已自动刷新，但可能需要重启浏览器"
echo "3. 某些浏览器会缓存 DNS 结果较长时间"
echo ""

