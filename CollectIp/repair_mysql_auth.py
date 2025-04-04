#!/usr/bin/env python3
"""
MySQL认证问题检查脚本
用于诊断和修复CollectIp项目的MySQL连接问题
"""
import os
import sys
import subprocess
import re
import pymysql

def print_header(title):
    """打印带标题的分隔线"""
    print("\n" + "=" * 60)
    print(f"{title}")
    print("=" * 60)

def get_db_settings():
    """从Django设置文件提取数据库设置"""
    settings_path = "/usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py"
    
    if not os.path.exists(settings_path):
        print(f"错误: 设置文件未找到 - {settings_path}")
        return None
    
    try:
        with open(settings_path, 'r') as f:
            content = f.read()
        
        # 用正则表达式提取数据库设置
        db_name = re.search(r"'NAME':\s*'([^']*)'", content)
        db_user = re.search(r"'USER':\s*'([^']*)'", content)
        db_pass = re.search(r"'PASSWORD':\s*'([^']*)'", content)
        db_host = re.search(r"'HOST':\s*'([^']*)'", content)
        db_port = re.search(r"'PORT':\s*'([^']*)'", content)
        
        settings = {
            'NAME': db_name.group(1) if db_name else None,
            'USER': db_user.group(1) if db_user else None,
            'PASSWORD': db_pass.group(1) if db_pass else None,
            'HOST': db_host.group(1) if db_host else None,
            'PORT': db_port.group(1) if db_port else None
        }
        
        return settings
    except Exception as e:
        print(f"提取数据库设置时出错: {e}")
        return None

def test_mysql_connection(user, password, host='localhost', port=3306):
    """测试MySQL连接"""
    try:
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=int(port) if port else 3306
        )
        connection.close()
        return True, "连接成功"
    except pymysql.Error as e:
        return False, f"错误: {e}"

def check_mysql_service():
    """检查MySQL服务状态"""
    try:
        result = subprocess.run(["systemctl", "status", "mysql"], 
                                capture_output=True, text=True)
        if "active (running)" in result.stdout:
            return True, "MySQL服务正在运行"
        else:
            return False, "MySQL服务未运行"
    except Exception as e:
        return False, f"检查MySQL服务时出错: {e}"

def check_mysql_user(user, password=None):
    """检查MySQL用户和认证插件"""
    try:
        sql_cmd = f"mysql -u root -e \"SELECT user, host, plugin FROM mysql.user WHERE user='{user}';\""
        if password:
            sql_cmd = f"mysql -u root -p{password} -e \"SELECT user, host, plugin FROM mysql.user WHERE user='{user}';\""
        
        result = subprocess.run(sql_cmd, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"检查MySQL用户时出错: {e}"

def update_db_password(new_password):
    """更新Django设置文件中的数据库密码"""
    settings_path = "/usr/local/CollectIp/CollectIp/CollectIp/settings_optimized.py"
    
    # 备份设置文件
    backup_path = f"{settings_path}.bak"
    try:
        subprocess.run(["cp", settings_path, backup_path])
        print(f"设置文件已备份到 {backup_path}")
    except Exception as e:
        print(f"备份设置文件时出错: {e}")
        return False
    
    # 更新密码
    try:
        with open(settings_path, 'r') as f:
            content = f.read()
        
        # 替换密码
        new_content = re.sub(r"'PASSWORD':\s*'[^']*'", f"'PASSWORD': '{new_password}'", content)
        
        with open(settings_path, 'w') as f:
            f.write(new_content)
        
        print(f"设置文件中的数据库密码已更新")
        return True
    except Exception as e:
        print(f"更新设置文件时出错: {e}")
        return False

def reset_mysql_root_password(new_password):
    """尝试重置MySQL root密码"""
    print("这将尝试重置MySQL root用户密码")
    print("警告: 此操作需要root权限")
    
    try:
        # 停止MySQL服务
        subprocess.run(["sudo", "systemctl", "stop", "mysql"])
        
        # 以安全模式启动MySQL
        subprocess.run(["sudo", "mkdir", "-p", "/var/run/mysqld"])
        subprocess.run(["sudo", "chown", "mysql:mysql", "/var/run/mysqld"])
        
        # 启动MySQL安全模式
        safe_process = subprocess.Popen(["sudo", "mysqld_safe", "--skip-grant-tables"], 
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("等待MySQL安全模式启动...")
        import time
        time.sleep(5)
        
        # 重置密码
        cmd = f"sudo mysql -e \"USE mysql; ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '{new_password}'; FLUSH PRIVILEGES;\""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # 停止安全模式的MySQL
        subprocess.run(["sudo", "killall", "mysqld"])
        time.sleep(2)
        
        # 重启MySQL服务
        subprocess.run(["sudo", "systemctl", "start", "mysql"])
        
        # 测试新密码
        success, message = test_mysql_connection("root", new_password)
        if success:
            print("MySQL root密码重置成功")
            return True
        else:
            print(f"密码重置后测试连接失败: {message}")
            return False
    except Exception as e:
        print(f"重置MySQL密码时出错: {e}")
        return False

def restart_apache():
    """重启Apache服务"""
    try:
        subprocess.run(["sudo", "systemctl", "restart", "apache2"])
        print("Apache服务已重启")
        return True
    except Exception as e:
        print(f"重启Apache时出错: {e}")
        return False

def main():
    print_header("MySQL认证问题检查")
    
    # 检查MySQL服务
    service_running, service_message = check_mysql_service()
    if service_running:
        print(f"✅ {service_message}")
    else:
        print(f"❌ {service_message}")
        print("请先启动MySQL服务: sudo systemctl start mysql")
        return
    
    # 获取当前数据库设置
    db_settings = get_db_settings()
    if not db_settings:
        print("❌ 无法获取数据库设置")
        return
    
    print("\n当前数据库设置:")
    print(f"数据库: {db_settings['NAME']}")
    print(f"用户: {db_settings['USER']}")
    print(f"密码: {'*' * len(db_settings['PASSWORD']) if db_settings['PASSWORD'] else '空'}")
    print(f"主机: {db_settings['HOST']}")
    print(f"端口: {db_settings['PORT']}")
    
    # 测试当前设置
    success, message = test_mysql_connection(
        user=db_settings['USER'],
        password=db_settings['PASSWORD'],
        host=db_settings['HOST'],
        port=db_settings['PORT']
    )
    
    if success:
        print(f"✅ MySQL连接测试成功: {message}")
        print("\n如果Django仍然无法连接数据库，可能是其他问题。")
        print("请检查数据库是否存在，以及用户权限是否正确。")
    else:
        print(f"❌ MySQL连接测试失败: {message}")
        
        while True:
            print("\n选择要执行的操作:")
            print("1. 更新Django设置中的数据库密码")
            print("2. 重置MySQL root密码")
            print("3. 退出")
            
            choice = input("请输入选项 (1-3): ")
            
            if choice == "1":
                new_password = input("请输入正确的MySQL密码: ")
                if update_db_password(new_password):
                    restart_apache()
                    print("已更新Django设置文件，请尝试再次访问网站。")
            elif choice == "2":
                new_password = input("请输入新的MySQL root密码: ")
                if reset_mysql_root_password(new_password):
                    if update_db_password(new_password):
                        restart_apache()
                        print("已重置MySQL密码并更新Django设置，请尝试再次访问网站。")
            elif choice == "3":
                break
            else:
                print("无效的选项，请重新输入。")

if __name__ == "__main__":
    main() 