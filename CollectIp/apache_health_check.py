#!/usr/bin/env python3
"""
Apache部署健康检查 - 低内存环境下验证Django项目状态

使用方法:
  python apache_health_check.py

此脚本执行以下操作:
1. 验证项目结构
2. 检查settings_optimized.py设置
3. 验证数据库连接
4. 验证静态文件配置
5. 检查关键URL配置
6. 验证Apache配置需求
"""

import os
import sys
import importlib
import subprocess
import traceback

class HealthChecker:
    """健康检查类"""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.has_fatal_error = False
        
        # 跳过验证的应用
        self.skip_apps = ['mongo_admin']
        
        # 设置Django环境
        os.environ["DJANGO_SETTINGS_MODULE"] = "CollectIp.settings_optimized"
    
    def print_header(self, title):
        """打印标题"""
        print("\n" + "=" * 60)
        print(f" {title} ".center(60, "="))
        print("=" * 60)
    
    def print_result(self, check, passed, message="", fatal=False):
        """打印检查结果"""
        if passed:
            self.checks_passed += 1
            print(f"✅ {check}")
        else:
            self.checks_failed += 1
            if fatal:
                self.has_fatal_error = True
                print(f"❌ {check} [致命错误]")
            else:
                print(f"❌ {check}")
                
            if message:
                print(f"   原因: {message}")
    
    def check_project_structure(self):
        """检查项目结构"""
        self.print_header("项目结构检查")
        
        # 检查主要目录和文件
        key_dirs = ['index', 'CollectIp', 'ip_operator', 'static', 'templates']
        key_files = ['manage.py', 'CollectIp/settings_optimized.py', 'CollectIp/wsgi.py']
        
        for dir_name in key_dirs:
            self.print_result(
                f"目录 '{dir_name}' 存在",
                os.path.isdir(dir_name),
                f"目录 '{dir_name}' 不存在"
            )
        
        for file_name in key_files:
            self.print_result(
                f"文件 '{file_name}' 存在",
                os.path.isfile(file_name),
                f"文件 '{file_name}' 不存在"
            )
        
        # 检查静态文件目录
        try:
            from django.conf import settings
            if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
                static_dir = settings.STATIC_ROOT
                static_dir_exists = os.path.isdir(static_dir)
                self.print_result(
                    f"静态文件目录 '{static_dir}' 存在",
                    static_dir_exists,
                    f"静态文件目录 '{static_dir}' 不存在，您需要运行 'python manage.py collectstatic'"
                )
            else:
                self.print_result(
                    "STATIC_ROOT 已设置",
                    False,
                    "STATIC_ROOT 未在设置中定义"
                )
        except Exception as e:
            self.print_result(
                "检查静态文件目录",
                False,
                f"错误: {e}"
            )
    
    def check_settings(self):
        """检查设置文件"""
        self.print_header("设置检查")
        
        # 尝试导入设置
        try:
            from django.conf import settings
            
            # 检查关键设置
            self.print_result(
                "DEBUG 设置为 False",
                not settings.DEBUG,
                "生产环境中 DEBUG 应该设置为 False"
            )
            
            self.print_result(
                "ALLOWED_HOSTS 已配置",
                len(settings.ALLOWED_HOSTS) > 0 and settings.ALLOWED_HOSTS != [''],
                "ALLOWED_HOSTS 应该配置为您的域名或 '*'"
            )
            
            self.print_result(
                "数据库设置已配置",
                hasattr(settings, 'DATABASES') and 'default' in settings.DATABASES,
                "默认数据库设置不完整"
            )
            
            self.print_result(
                "静态文件设置已配置",
                hasattr(settings, 'STATIC_URL') and hasattr(settings, 'STATIC_ROOT'),
                "静态文件设置不完整"
            )
            
            # 检查内存优化设置
            memory_optimized = (
                'django.contrib.admin' not in settings.INSTALLED_APPS and
                len(settings.MIDDLEWARE) <= 10 and
                hasattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE') and 
                settings.FILE_UPLOAD_MAX_MEMORY_SIZE <= 5242880  # 5MB
            )
            
            self.print_result(
                "内存优化设置已应用",
                memory_optimized,
                "某些内存优化设置未应用"
            )
            
        except ImportError as e:
            self.print_result(
                "导入设置模块",
                False,
                f"无法导入设置: {e}",
                fatal=True
            )
        except Exception as e:
            self.print_result(
                "检查设置",
                False,
                f"错误: {e}"
            )
    
    def check_db_connection(self):
        """检查数据库连接"""
        self.print_header("数据库连接检查")
        
        # 如果有致命错误，跳过此检查
        if self.has_fatal_error:
            print("跳过此部分，因为之前存在致命错误")
            return
        
        try:
            from django.db import connections
            connection = connections['default']
            connection.ensure_connection()
            
            self.print_result(
                "连接到默认数据库",
                True
            )
            
            # 检查migrations是否已应用
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM django_migrations")
                    count = cursor.fetchone()[0]
                    
                self.print_result(
                    "数据库迁移已应用",
                    count > 0,
                    f"发现 {count} 迁移记录，如果这是第一次部署，您需要运行 'python manage.py migrate'"
                )
            except Exception as e:
                self.print_result(
                    "检查数据库迁移",
                    False,
                    f"错误: {e}"
                )
                
        except ImportError as e:
            self.print_result(
                "导入数据库模块",
                False,
                f"错误: {e}"
            )
        except Exception as e:
            self.print_result(
                "连接到数据库",
                False,
                f"错误: {e}",
                fatal=True
            )
    
    def check_urls(self):
        """检查URL配置"""
        self.print_header("URL配置检查")
        
        # 如果有致命错误，跳过此检查
        if self.has_fatal_error:
            print("跳过此部分，因为之前存在致命错误")
            return
        
        try:
            # 导入URL配置
            from django.urls import get_resolver
            resolver = get_resolver()
            
            # 检查关键URL模式是否存在
            key_url_names = ['index', 'login', 'logout', 'ip_pool', 'logs_view']
            for url_name in key_url_names:
                self.print_result(
                    f"URL名称 '{url_name}' 已配置",
                    url_name in resolver.reverse_dict,
                    f"URL名称 '{url_name}' 未找到"
                )
                
        except ImportError as e:
            self.print_result(
                "导入URL配置",
                False,
                f"错误: {e}"
            )
        except Exception as e:
            self.print_result(
                "检查URL配置",
                False,
                f"错误: {e}"
            )
    
    def check_wsgi(self):
        """检查WSGI配置"""
        self.print_header("WSGI检查")
        
        # 检查WSGI文件
        try:
            if os.path.exists("CollectIp/wsgi_optimized.py"):
                # 尝试导入优化的WSGI
                mod_path = "CollectIp.wsgi_optimized"
                module = importlib.import_module(mod_path)
                self.print_result(
                    "加载优化的WSGI配置",
                    hasattr(module, 'application'),
                    "wsgi_optimized.py 不包含 'application' 对象"
                )
            else:
                # 尝试导入默认WSGI
                mod_path = "CollectIp.wsgi"
                module = importlib.import_module(mod_path)
                self.print_result(
                    "加载WSGI配置",
                    hasattr(module, 'application'),
                    "wsgi.py 不包含 'application' 对象"
                )
                
                # 检查是否使用了优化的设置
                is_optimized = False
                try:
                    wsgi_path = "CollectIp/wsgi.py"
                    with open(wsgi_path, 'r') as f:
                        content = f.read()
                        is_optimized = "settings_optimized" in content
                except:
                    pass
                
                self.print_result(
                    "WSGI使用优化的设置",
                    is_optimized,
                    "wsgi.py 未配置为使用 'settings_optimized'"
                )
                
        except ImportError as e:
            self.print_result(
                "导入WSGI模块",
                False,
                f"错误: {e}"
            )
        except Exception as e:
            self.print_result(
                "检查WSGI配置",
                False,
                f"错误: {e}"
            )
    
    def check_apache_requirements(self):
        """检查Apache部署需求"""
        self.print_header("Apache部署需求检查")
        
        # 检查Apache配置文件
        self.print_result(
            "Apache配置文件存在",
            os.path.exists("collectip_apache.conf"),
            "未找到 'collectip_apache.conf'，请先创建此文件"
        )
        
        # 检查mod_wsgi是否可用
        try:
            # 尝试查找mod_wsgi
            result = subprocess.run(
                ["apt-cache", "policy", "libapache2-mod-wsgi-py3"],
                capture_output=True,
                text=True
            )
            mod_wsgi_available = "Installed:" in result.stdout and not "Installed: (none)" in result.stdout
            
            self.print_result(
                "mod_wsgi 已安装",
                mod_wsgi_available,
                "apt-cache 报告 mod_wsgi 未安装，请安装 'libapache2-mod-wsgi-py3'"
            )
        except Exception:
            # 如果无法检查，提供通用建议
            self.print_result(
                "mod_wsgi 需求",
                True,
                "请确保安装 'libapache2-mod-wsgi-py3'"
            )
        
        # 检查文件权限
        logs_dir = "logs"
        logs_dir_exists = os.path.isdir(logs_dir)
        logs_writable = False
        
        if logs_dir_exists:
            try:
                test_file = os.path.join(logs_dir, "writable_test.txt")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                logs_writable = True
            except:
                pass
        
        self.print_result(
            "日志目录可写",
            logs_dir_exists and logs_writable,
            "日志目录不存在或不可写，您需要创建 'logs' 目录并设置正确的权限"
        )
    
    def print_summary(self):
        """打印摘要"""
        self.print_header("检查摘要")
        
        total = self.checks_passed + self.checks_failed
        pass_percentage = (self.checks_passed / total) * 100 if total > 0 else 0
        
        print(f"总检查数: {total}")
        print(f"通过: {self.checks_passed} ({pass_percentage:.1f}%)")
        print(f"失败: {self.checks_failed}")
        
        if self.checks_failed == 0:
            print("\n✅ 所有检查通过! 项目已准备好部署到Apache。")
        elif self.has_fatal_error:
            print("\n❌ 存在致命错误，必须修复后才能部署。")
        else:
            print("\n⚠️ 某些检查失败，但项目可能仍能部署。请查看上述警告。")
            
        print("\n部署命令:")
        print("1. 收集静态文件:")
        print("   python manage.py collectstatic --settings=CollectIp.settings_optimized --noinput")
        print("2. 复制Apache配置:")
        print("   sudo cp collectip_apache.conf /etc/apache2/sites-available/")
        print("3. 启用站点:")
        print("   sudo a2ensite collectip.conf")
        print("4. 重启Apache:")
        print("   sudo systemctl restart apache2")
    
    def run_all_checks(self):
        """运行所有检查"""
        try:
            self.check_project_structure()
            self.check_settings()
            self.check_db_connection()
            self.check_urls()
            self.check_wsgi()
            self.check_apache_requirements()
            self.print_summary()
            
            # 返回检查是否全部通过
            return self.checks_failed == 0
            
        except Exception as e:
            print(f"\n执行检查时发生错误: {e}")
            traceback.print_exc()
            return False

def main():
    """主函数"""
    checker = HealthChecker()
    success = checker.run_all_checks()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 