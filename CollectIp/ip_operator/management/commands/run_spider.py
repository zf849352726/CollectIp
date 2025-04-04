from django.core.management.base import BaseCommand
import os
import sys
import subprocess

class Command(BaseCommand):
    help = '运行CollectIP爬虫'

    def handle(self, *args, **options):
        self.stdout.write('开始运行爬虫...')
        
        # 设置爬虫项目路径
        spider_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'crawl_ip', 'crawl_ip'
        )
        
        # 记录当前路径
        current_path = os.getcwd()
        
        try:
            # 切换到爬虫项目目录
            os.chdir(spider_path)
            
            # 运行爬虫
            result = subprocess.run(['scrapy', 'crawl', 'collectip'], 
                                    capture_output=True, 
                                    text=True)
            
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS('爬虫运行成功'))
                self.stdout.write(result.stdout)
            else:
                self.stdout.write(self.style.ERROR('爬虫运行失败'))
                self.stdout.write(result.stderr)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'爬虫执行错误: {e}'))
        
        finally:
            # 恢复原来的路径
            os.chdir(current_path)