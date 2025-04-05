#!/bin/bash
# Git合并冲突处理脚本

echo "===== 开始处理Git合并冲突 ====="

# 首先备份当前的设置文件
cp CollectIp/CollectIp/settings_optimized.py CollectIp/CollectIp/settings_optimized.py.local

echo "已备份当前设置文件到 settings_optimized.py.local"

# 暂存当前更改
echo "暂存当前所有更改..."
git stash

# 拉取远程更改
echo "拉取远程更改..."
git pull

# 恢复本地密码设置
echo "恢复本地的数据库密码设置..."
sed -i "s/'PASSWORD': '.*'/'PASSWORD': '123456'/" CollectIp/CollectIp/settings_optimized.py

echo "===== 合并完成 ====="
echo "本地数据库密码(123456)已保留，并且拉取了远程的其他更改。"
echo "如果需要查看原始的本地设置文件，可以查看 settings_optimized.py.local" 