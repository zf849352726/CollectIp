#!/usr/bin/env python
"""
Apache部署调试工具
用于诊断CollectIp项目的Apache部署问题
"""
import os
import sys
import subprocess
import socket
import re
from datetime import datetime

def print_header(title):
    """打印带标题的分隔线"""
    print("\n" + "=" * 60)
    print(f"{title}")
    print("=" * 60)

def check_apache_install():
    """检查Apache安装状态"""
    print_header("Apache安装检查")
    
    try:
        result = subprocess.run(["apache2ctl", "-v"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Apache已安装: {result.stdout.strip()}")
        else:
            print(f"❌ Apache安装存在问题: {result.stderr.strip()}")
    except Exception as e:
        print(f"❌ 检查Apache安装时出错: {str(e)}")
    
    # 检查Apache状态
    try:
        result = subprocess.run(["systemctl", "status", "apache2"], capture_output=True, text=True)
        status_line = next((line for line in result.stdout.split('\n') if "Active:" in line), "")
        if "active (running)" in status_line:
            print(f"✅ Apache服务运行中: {status_line.strip()}")
        else:
            print(f"❌ Apache服务未运行: {status_line.strip()}")
    except Exception as e:
        print(f"❌ 检查Apache状态时出错: {str(e)}")

def check_mod_wsgi():
    """检查mod_wsgi模块"""
    print_header("mod_wsgi模块检查")
    
    try:
        result = subprocess.run(["apache2ctl", "-M"], capture_output=True, text=True)
        modules = result.stdout
        
        if "wsgi_module" in modules:
            print("✅ mod_wsgi模块已加载")
        else:
            print("❌ mod_wsgi模块未加载")
            print("💡 建议: 运行 'sudo apt-get install libapache2-mod-wsgi-py3' 安装模块")
            print("         然后运行 'sudo a2enmod wsgi' 启用模块")
    except Exception as e:
        print(f"❌ 检查mod_wsgi时出错: {str(e)}")

def check_site_config():
    """检查站点配置"""
    print_header("站点配置检查")
    
    # 检查站点是否启用
    try:
        result = subprocess.run(["apache2ctl", "-S"], capture_output=True, text=True)
        output = result.stdout
        
        # 查找默认站点信息
        default_site = re.search(r'default\s+server\s+(.*?)\s+\((.*?)\)', output)
        if default_site:
            default_server = default_site.group(1)
            default_config = default_site.group(2)
            if "000-default" in default_config:
                print(f"❌ 默认站点 (000-default) 仍然是默认站点: {default_config}")
                print("💡 建议: 运行 'sudo a2dissite 000-default.conf' 禁用默认站点")
            else:
                print(f"✅ 默认站点配置: {default_config}")
        
        # 查找collectip站点信息
        if "collectip_apache.conf" in output or "collectip.conf" in output:
            print("✅ CollectIp站点配置已启用")
        else:
            print("❌ CollectIp站点配置未启用")
            print("💡 建议: 运行 'sudo a2ensite collectip_apache.conf' 启用CollectIp站点")
    except Exception as e:
        print(f"❌ 检查站点配置时出错: {str(e)}")
    
    # 检查配置文件
    if os.path.exists("/etc/apache2/sites-available/collectip_apache.conf"):
        print("✅ collectip_apache.conf文件存在于sites-available")
    else:
        print("❌ collectip_apache.conf文件不存在于sites-available")
    
    if os.path.exists("/etc/apache2/sites-enabled/collectip_apache.conf"):
        print("✅ collectip_apache.conf文件存在于sites-enabled")
    else:
        print("❌ collectip_apache.conf文件不存在于sites-enabled")

def check_django_files():
    """检查Django项目文件"""
    print_header("Django项目文件检查")
    
    project_path = "/usr/local/CollectIp/CollectIp"
    wsgi_path = os.path.join(project_path, "CollectIp", "wsgi.py")
    settings_path = os.path.join(project_path, "CollectIp", "settings_optimized.py")
    static_path = os.path.join(project_path, "staticfiles")
    
    # 检查项目目录
    if os.path.exists(project_path):
        print(f"✅ 项目目录存在: {project_path}")
    else:
        print(f"❌ 项目目录不存在: {project_path}")
    
    # 检查wsgi.py
    if os.path.exists(wsgi_path):
        print(f"✅ wsgi.py文件存在: {wsgi_path}")
        # 检查权限
        wsgi_perms = oct(os.stat(wsgi_path).st_mode)[-3:]
        if wsgi_perms == "644" or wsgi_perms == "664" or wsgi_perms == "755":
            print(f"✅ wsgi.py文件权限正确: {wsgi_perms}")
        else:
            print(f"❌ wsgi.py文件权限不正确: {wsgi_perms}")
            print("💡 建议: 运行 'sudo chmod 644 wsgi.py' 修正权限")
    else:
        print(f"❌ wsgi.py文件不存在: {wsgi_path}")
    
    # 检查优化后的设置文件
    if os.path.exists(settings_path):
        print(f"✅ settings_optimized.py文件存在: {settings_path}")
    else:
        print(f"❌ settings_optimized.py文件不存在: {settings_path}")
    
    # 检查静态文件目录
    if os.path.exists(static_path):
        print(f"✅ 静态文件目录存在: {static_path}")
        # 检查静态文件
        static_files = len(os.listdir(static_path))
        print(f"   静态文件数量: {static_files}")
    else:
        print(f"❌ 静态文件目录不存在: {static_path}")
        print("💡 建议: 运行 'python manage.py collectstatic --settings=CollectIp.settings_optimized --noinput' 收集静态文件")

def check_apache_logs():
    """检查Apache日志"""
    print_header("Apache日志检查")
    
    error_log = "/var/log/apache2/collectip-error.log"
    access_log = "/var/log/apache2/collectip-access.log"
    
    # 检查错误日志
    if os.path.exists(error_log):
        print(f"✅ 错误日志文件存在: {error_log}")
        try:
            result = subprocess.run(["tail", "-n", "10", error_log], capture_output=True, text=True)
            print("\n最后10行错误日志:")
            print("-" * 40)
            print(result.stdout)
            print("-" * 40)
        except Exception as e:
            print(f"❌ 读取错误日志时出错: {str(e)}")
    else:
        print(f"❌ 错误日志文件不存在: {error_log}")
    
    # 检查访问日志
    if os.path.exists(access_log):
        print(f"✅ 访问日志文件存在: {access_log}")
    else:
        print(f"❌ 访问日志文件不存在: {access_log}")

def check_network():
    """检查网络和端口配置"""
    print_header("网络配置检查")
    
    # 获取主机名和IP
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        print(f"主机名: {hostname}")
        print(f"IP地址: {ip}")
    except Exception as e:
        print(f"❌ 获取主机信息时出错: {str(e)}")
    
    # 检查80端口是否被占用
    try:
        result = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True)
        if ":80 " in result.stdout:
            for line in result.stdout.split('\n'):
                if ":80 " in line:
                    print(f"✅ 端口80被占用: {line.strip()}")
        else:
            print("❌ 端口80未被占用")
    except Exception as e:
        print(f"❌ 检查端口时出错: {str(e)}")

def print_summary():
    """打印总结和建议"""
    print_header("问题排查建议")
    
    print("1. 确保mod_wsgi模块已安装且已启用")
    print("   sudo apt-get install libapache2-mod-wsgi-py3")
    print("   sudo a2enmod wsgi")
    
    print("\n2. 确保已禁用默认站点并启用CollectIp站点")
    print("   sudo a2dissite 000-default.conf")
    print("   sudo a2ensite collectip_apache.conf")
    
    print("\n3. 确保collectip_apache.conf配置正确")
    print("   - WSGIScriptAlias路径是否正确")
    print("   - python-home和python-path是否正确")
    print("   - DocumentRoot路径是否正确")
    print("   - 静态文件和媒体文件路径是否正确")
    
    print("\n4. 确保文件和目录权限正确")
    print("   sudo chmod 644 /usr/local/CollectIp/CollectIp/CollectIp/wsgi.py")
    print("   sudo chmod -R 755 /usr/local/CollectIp/CollectIp/staticfiles")
    print("   sudo chown -R www-data:www-data /usr/local/CollectIp/CollectIp/staticfiles")
    
    print("\n5. 重启Apache服务")
    print("   sudo systemctl restart apache2")
    
    print("\n6. 仔细查看错误日志")
    print("   sudo tail -f /var/log/apache2/collectip-error.log")

def main():
    """主函数"""
    print("=" * 60)
    print(f"CollectIp Apache部署调试工具 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    check_apache_install()
    check_mod_wsgi()
    check_site_config()
    check_django_files()
    check_apache_logs()
    check_network()
    print_summary()

if __name__ == "__main__":
    main() 