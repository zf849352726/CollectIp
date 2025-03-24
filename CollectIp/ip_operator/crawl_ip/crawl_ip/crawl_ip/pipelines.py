# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import pymysql
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class SaveIpPipeline:
    def __init__(self):
        # 从Django settings获取数据库配置
        self.db_settings = settings.DATABASES['default']
        self.establish_connection()
        
    def establish_connection(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.db_settings['HOST'],
                user=self.db_settings['USER'],
                password=self.db_settings['PASSWORD'],
                database=self.db_settings['NAME'],
                port=int(self.db_settings['PORT']),
                charset='utf8mb4'
            )
            self.cursor = self.connection.cursor()
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise

    def process_item(self, item, spider):
        try:
            adapter = ItemAdapter(item)
            
            # 直接获取server字段
            server = adapter.get('server', '')
            
            # 准备SQL语句，包含所有必需的字段，并用反引号括起关键字
            sql = """
                INSERT INTO index_ipdata (
                    `server`, `ping`, `speed`, `uptime1`, `uptime2`, `type_data`, `country`, 
                    `ssl`, `conn`, `post`, `last_work_time`, `score`, `created_at`, `updated_at`
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s, NOW(), NOW()
                )
                ON DUPLICATE KEY UPDATE
                `country` = VALUES(`country`),
                `type_data` = VALUES(`type_data`),
                `conn` = VALUES(`conn`),
                `ssl` = VALUES(`ssl`),
                `post` = VALUES(`post`),
                `updated_at` = NOW()
            """
            
            # 执行SQL
            self.cursor.execute(sql, (
                server,
                adapter.get('ping', None),  # 延迟，可能为空
                adapter.get('speed', None),  # 速度，可能为空
                adapter.get('uptime1', 'N/A'),  # 上传时间1
                adapter.get('uptime2', 'N/A'),  # 上传时间2
                adapter.get('type_data', 'Unknown'),
                adapter.get('country', 'Unknown'),  # 国家
                adapter.get('ssl', 'N/A'),  # SSL支持
                adapter.get('conn', 'N/A'),  # 连接类型
                adapter.get('post', 'N/A'),  # POST支持
                adapter.get('last_work_time', 'N/A'),  # 最近工作时间
                100  # 默认分数
            ))
            
            self.connection.commit()
            spider.logger.info(f"保存IP记录: {server}")
            
        except Exception as e:
            spider.logger.error(f"保存IP数据失败: {str(e)}")
            spider.logger.error(f"错误详情: {item}")
            self.connection.rollback()
            
        return item

    def close_spider(self, spider):
        """关闭数据库连接"""
        self.cursor.close()
        self.connection.close()

# 添加兼容旧配置的类名
class CrawlIpPipeline(SaveIpPipeline):
    """兼容旧配置的管道类"""
    pass