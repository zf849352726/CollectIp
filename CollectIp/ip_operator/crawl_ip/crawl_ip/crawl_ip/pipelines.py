# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import pymysql
import logging
import os
import sys
from django.conf import settings
from django.utils import timezone
from index.mongodb_utils import MongoDBClient
# 修复导入问题
# 获取当前文件的目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 尝试查找项目根目录
def find_project_root():
    """尝试查找项目根目录"""
    # 可能的项目根目录和utlis目录列表
    possible_roots = []
    
    # 从当前目录向上查找，最多查找5级
    current_path = CURRENT_DIR
    for _ in range(5):
        parent_path = os.path.dirname(current_path)
        # 检查是否有manage.py，这通常表示Django项目根目录
        if os.path.isfile(os.path.join(parent_path, 'manage.py')):
            possible_roots.append(parent_path)
        # 检查是否有CollectIp目录，这可能是中间目录
        if os.path.basename(parent_path) == 'CollectIp':
            # 检查上一级目录是否有manage.py
            grandparent = os.path.dirname(parent_path)
            if os.path.isfile(os.path.join(grandparent, 'manage.py')):
                possible_roots.append(grandparent)
        # 向上移动一级
        current_path = parent_path
    
    # 添加常见的部署路径
    possible_roots.extend([
        '/usr/local/CollectIp',
        '/var/www/CollectIp',
        '/var/www/html/CollectIp'
    ])
    
    # 去除重复项
    possible_roots = list(set(possible_roots))
    
    return possible_roots

# 尝试加载TextProcessor
TEXT_PROCESSOR_LOADED = False

def load_text_processor():
    """尝试加载TextProcessor，使用多种可能的路径"""
    global TEXT_PROCESSOR_LOADED
    
    # 如果已经加载，直接返回
    if TEXT_PROCESSOR_LOADED:
        return True
    
    # 记录尝试日志
    logger = logging.getLogger(__name__)
    logger.info("尝试导入TextProcessor...")
    
    # 获取可能的项目根目录
    project_roots = find_project_root()
    logger.info(f"找到可能的项目根目录: {project_roots}")
    
    # 可能的导入路径列表
    import_paths = [
        # 直接导入
        'from utlis.text_utils import TextProcessor',
        # 从CollectIp导入
        'from CollectIp.utlis.text_utils import TextProcessor',
        # 尝试绝对路径导入
    ]
    
    # 添加项目根目录到sys.path并尝试导入
    for root in project_roots:
        if root not in sys.path:
            sys.path.insert(0, root)
            logger.info(f"添加路径到sys.path: {root}")
    
    # 尝试不同的导入路径
    for import_path in import_paths:
        try:
            logger.info(f"尝试导入: {import_path}")
            exec(import_path)
            logger.info(f"成功导入TextProcessor")
            TEXT_PROCESSOR_LOADED = True
            return True
        except ImportError as e:
            logger.warning(f"导入失败: {import_path}, 错误: {e}")
    
    # 如果前面的导入都失败了，再尝试一次直接导入，可能前面的步骤修改了sys.path
    try:
        # 尝试直接导入
        from utlis.text_utils import TextProcessor
        logger.info("成功导入TextProcessor")
        TEXT_PROCESSOR_LOADED = True
        return True
    except ImportError as e:
        logger.error(f"所有导入尝试都失败: {e}")
        return False

# 尝试导入TextProcessor
try:
    # 首先尝试直接导入
    try:
        from utlis.text_utils import TextProcessor
        logging.info("直接导入TextProcessor成功")
    except ImportError:
        # 然后尝试从CollectIp导入
        try:
            from CollectIp.utlis.text_utils import TextProcessor
            logging.info("从CollectIp导入TextProcessor成功")
        except ImportError:
            # 使用我们的自定义函数尝试加载
            if not load_text_processor():
                # 如果所有尝试都失败，创建一个简单的替代类
                logging.warning("创建TextProcessor替代类")
                class TextProcessor:
                    @staticmethod
                    def clean_text(text):
                        """清洗文本，去除无效字符"""
                        if not text:
                            return ""
                        # 简单的文本清洗
                        import re
                        # 去除HTML标签
                        text = re.sub(r'<[^>]+>', '', text)
                        # 去除URL
                        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
                        # 去除特殊字符和多余空格
                        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
                        text = re.sub(r'\s+', ' ', text)
                        # 去除首尾空格
                        text = text.strip()
                        return text
                    
                    @staticmethod
                    def analyze_sentiment(text):
                        """简单的情感分析"""
                        return 0, 0.5
                    
                    @staticmethod
                    def extract_keywords(text, top_n=5):
                        """提取关键词"""
                        return []
except Exception as e:
    logging.error(f"导入或创建TextProcessor时出错: {e}")
    # 确保无论如何都有一个TextProcessor
    class TextProcessor:
        @staticmethod
        def clean_text(text):
            return text if text else ""
        
        @staticmethod
        def analyze_sentiment(text):
            return 0, 0.5
        
        @staticmethod
        def extract_keywords(text, top_n=5):
            return []

from datetime import datetime

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
            
            # 数据清洗 - 确保ping和speed字段为数字或None
            ping = adapter.get('ping', None)
            speed = adapter.get('speed', None)
            
            # 再次验证ping和speed是否为有效数字，若非数字则设为None
            if ping is not None and not isinstance(ping, (int, float)):
                try:
                    ping = float(ping) if ping and ping != '?' else None
                except (ValueError, TypeError):
                    logger.warning(f"无效的ping值: {ping}，已设为None")
                    ping = None
            
            if speed is not None and not isinstance(speed, (int, float)):
                try:
                    speed = float(speed) if speed and speed != '?' else None
                except (ValueError, TypeError):
                    logger.warning(f"无效的speed值: {speed}，已设为None")
                    speed = None
            
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
            
            # 截断长字符串，确保不超过数据库字段长度限制
            uptime1 = adapter.get('uptime1', 'N/A')[:5]  # 最大长度5
            uptime2 = adapter.get('uptime2', 'N/A')[:5]  # 最大长度5
            type_data = adapter.get('type_data', 'Unknown')[:20]  # 最大长度20
            country = adapter.get('country', 'Unknown')[:20]  # 最大长度20
            ssl = adapter.get('ssl', 'N/A')[:50]  # 最大长度50
            conn = adapter.get('conn', 'N/A')[:50]  # 最大长度50
            post = adapter.get('post', 'N/A')[:50]  # 最大长度50
            last_work_time = adapter.get('last_work_time', 'N/A')[:30]  # 最大长度30
            
            # 执行SQL
            self.cursor.execute(sql, (
                server,
                ping,  # 延迟，已处理为数字或None
                speed,  # 速度，已处理为数字或None
                uptime1,  # 上传时间1
                uptime2,  # 上传时间2
                type_data,
                country,  # 国家
                ssl,  # SSL支持
                conn,  # 连接类型
                post,  # POST支持
                last_work_time,  # 最近工作时间
                100  # 默认分数
            ))
            
            self.connection.commit()
            spider.logger.info(f"保存IP记录: {server}")
            
        except Exception as e:
            spider.logger.error(f"保存IP数据失败: {str(e)}")
            spider.logger.error(f"错误详情: {dict(ItemAdapter(item))}")
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


class MoviePipeline:
    """处理电影数据的管道"""
    
    def __init__(self):
        """初始化数据库连接"""
        # 从Django settings获取数据库配置
        from django.conf import settings
        self.db_settings = settings.DATABASES['default']
        self.establish_connection()
        
    def establish_connection(self):
        """建立数据库连接"""
        try:
            import pymysql
            self.connection = pymysql.connect(
                host=self.db_settings['HOST'],
                user=self.db_settings['USER'],
                password=self.db_settings['PASSWORD'],
                database=self.db_settings['NAME'],
                port=int(self.db_settings['PORT']),
                charset='utf8mb4'
            )
            self.cursor = self.connection.cursor()
            logger.info("电影数据库连接成功")
        except Exception as e:
            logger.error(f"电影数据库连接失败: {str(e)}")
            raise
            
    def process_item(self, item, spider):
        """处理电影数据项"""
        from itemadapter import ItemAdapter
        
        # 只处理电影类型的数据
        if spider.name != 'douban_spider':
            return item
            
        adapter = ItemAdapter(item)
        
        # 确保必要字段存在
        if not adapter.get('title'):
            return item
            
        try:
            # 查询电影是否已存在
            sql_check = """
                SELECT id FROM index_movie 
                WHERE title = %s AND year = %s
            """
            self.cursor.execute(sql_check, (
                adapter.get('title', ''),
                adapter.get('year', '')
            ))
            result = self.cursor.fetchone()
            
            if result:
                # 更新现有电影数据
                movie_id = result[0]
                sql_update = """
                    UPDATE index_movie SET
                        director = %s,
                        actors = %s,
                        rating = %s,
                        rating_count = %s,
                        genre = %s,
                        region = %s,
                        duration = %s,
                        poster_url = %s,
                        summary = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """
                self.cursor.execute(sql_update, (
                    adapter.get('director', '未知'),
                    adapter.get('actors', '未知'),
                    adapter.get('rating', 0),
                    adapter.get('rating_count', 0),
                    adapter.get('genre', '未知'),
                    adapter.get('region', '未知'),
                    adapter.get('duration', '未知'),
                    adapter.get('poster_url', None),
                    adapter.get('summary', '暂无简介'),
                    movie_id
                ))
            else:
                # 插入新电影数据
                sql_insert = """
                    INSERT INTO index_movie (
                        title, director, actors, year, rating, 
                        rating_count, genre, region, duration,
                        poster_url, summary,
                        created_at, updated_at, is_published
                    ) VALUES (
                        %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, 
                        %s, %s,
                        NOW(), NOW(), FALSE
                    )
                """
                self.cursor.execute(sql_insert, (
                    adapter.get('title', ''),
                    adapter.get('director', '未知'),
                    adapter.get('actors', '未知'),
                    adapter.get('year', '未知'),
                    adapter.get('rating', 0),
                    adapter.get('rating_count', 0),
                    adapter.get('genre', '未知'),
                    adapter.get('region', '未知'),
                    adapter.get('duration', '未知'),
                    adapter.get('poster_url', None),
                    adapter.get('summary', '暂无简介')
                ))
                
                # 获取新插入的电影ID
                movie_id = self.cursor.lastrowid
                
            # 提交事务
            self.connection.commit()
            spider.logger.info(f"保存电影数据成功: {adapter.get('title')}")
            
            # 处理评论数据 (可以根据需要添加)
            # comments = adapter.get('comments', [])
            # if comments:
            #     self.save_comments(movie_id, comments)
                
        except Exception as e:
            spider.logger.error(f"保存电影数据失败: {str(e)}")
            self.connection.rollback()
            
        return item

    def save_comments(self, movie_id, comments):
        """保存电影评论"""
        pass  # 可以根据需要实现评论保存逻辑
            
    def close_spider(self, spider):
        """关闭数据库连接"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()

class CommentPipeline:
    """专门处理电影评论的管道，将评论数据存储到MongoDB"""
    
    def __init__(self):
        """初始化评论管道"""
        self.mongo_client = None
        self.batch_size = 50  # 批量处理大小
        self.comment_buffer = []
    
    def open_spider(self, spider):
        """爬虫启动时，初始化MongoDB连接"""
        if spider.name != 'douban_spider':
            return
            
        try:
            # 获取MongoDB客户端实例
            self.mongo_client = MongoDBClient.get_instance()
            spider.logger.info("CommentPipeline: MongoDB连接成功")
        except Exception as e:
            spider.logger.error(f"CommentPipeline: MongoDB连接失败: {str(e)}")
    
    def process_item(self, item, spider):
        """处理评论数据项"""
        # 只处理豆瓣爬虫的数据，并且包含评论数据
        if spider.name != 'douban_spider':
            return item
            
        # 检查是否有评论数据
        has_comments = 'comments' in item and item['comments']
        has_details = 'comment_details' in item and item['comment_details']
        
        if not (has_comments or has_details):
            return item
            
        try:
            # 获取电影信息
            movie_id = self._get_movie_id(item, spider)
            
            # 如果没有找到电影ID，则跳过处理
            if not movie_id:
                return item
                
            # 处理评论数据
            if has_details:
                # 使用详细评论数据
                self._process_comment_details(movie_id, item, spider)
            elif has_comments:
                # 使用旧的纯文本评论
                self._process_simple_comments(movie_id, item, spider)
                
            return item
            
        except Exception as e:
            spider.logger.error(f"CommentPipeline: 处理评论出错: {str(e)}")
            import traceback
            spider.logger.error(traceback.format_exc())
            return item
    
    def _get_movie_id(self, item, spider):
        """获取电影ID，如果不存在则尝试从数据库查询"""
        movie_id = item.get('id')
        movie_title = item.get('title', '')
        
        # 如果有movie_id，则直接返回
        if movie_id:
            return movie_id
            
        # 否则从数据库查询
        try:
            import pymysql
            from django.conf import settings

            # 获取MySQL连接配置
            db_settings = settings.DATABASES['default']
            
            # 建立连接
            connection = pymysql.connect(
                host=db_settings['HOST'],
                user=db_settings['USER'],
                password=db_settings['PASSWORD'],
                database=db_settings['NAME'],
                charset='utf8mb4'
            )
            
            try:
                with connection.cursor() as cursor:
                    # 查询电影ID
                    sql = "SELECT id FROM index_movie WHERE title = %s LIMIT 1"
                    cursor.execute(sql, (movie_title,))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
            finally:
                connection.close()
                
            # 如果没有找到，记录警告
            spider.logger.warning(f"CommentPipeline: 未找到电影ID，跳过评论处理: {movie_title}")
            return None
            
        except Exception as e:
            spider.logger.error(f"CommentPipeline: 查询电影ID失败: {str(e)}")
            return None
    
    def _process_comment_details(self, movie_id, item, spider):
        """处理详细评论数据"""
        comment_details = item['comment_details']
        spider.logger.info(f"CommentPipeline: 处理电影详细评论，电影ID: {movie_id}, 评论数: {len(comment_details)}")
        
        processed_comments = []
        
        # 获取爬虫使用的策略名称
        comment_strategy = None
        if hasattr(spider, 'comment_strategy') and hasattr(spider.comment_strategy, 'get_name'):
            comment_strategy = spider.comment_strategy.get_name()
        else:
            comment_strategy = 'sequential'  # 默认策略
        
        for comment in comment_details:
            if not comment.get('content', '').strip():
                continue
                
            # 文本清洗
            cleaned_text = TextProcessor.clean_text(comment['content'])
            
            # 情感分析
            sentiment, sentiment_score = TextProcessor.analyze_sentiment(cleaned_text)
            
            # 处理评论时间
            comment_time = comment.get('time', '')
            
            # 创建评论对象
            comment_data = {
                'movie_id': movie_id,
                'content': cleaned_text,
                'sentiment': sentiment,
                'sentiment_score': sentiment_score,
                'user_nickname': comment.get('user', '匿名用户'),
                'user_rating': comment.get('rating', '0'),
                'comment_time': comment_time,
                'keywords': TextProcessor.extract_keywords(cleaned_text, top_n=5),
                'comment_strategy': comment_strategy  # 添加策略信息
            }
            
            processed_comments.append(comment_data)
            
            # 添加到缓冲区
            self.comment_buffer.append(comment_data)
            
            # 如果缓冲区达到批量大小，则批量插入
            if len(self.comment_buffer) >= self.batch_size:
                self._flush_buffer(spider)
                
        spider.logger.info(f"CommentPipeline: 详细评论处理完成，电影ID: {movie_id}, 处理评论数: {len(processed_comments)}")
    
    def _process_simple_comments(self, movie_id, item, spider):
        """处理简单的纯文本评论数据（兼容旧版本）"""
        comments = item['comments']
        spider.logger.info(f"CommentPipeline: 处理电影纯文本评论，电影ID: {movie_id}, 评论数: {len(comments)}")
        
        processed_comments = []
        
        # 获取爬虫使用的策略名称
        comment_strategy = None
        if hasattr(spider, 'comment_strategy') and hasattr(spider.comment_strategy, 'get_name'):
            comment_strategy = spider.comment_strategy.get_name()
        else:
            comment_strategy = 'sequential'  # 默认策略
        
        for comment_item in comments:
            # 检查评论是否为字典对象（新格式）或字符串（旧格式）
            if isinstance(comment_item, dict):
                # 新格式的评论，已经是字典格式
                if not comment_item.get('content', '').strip():
                    continue
                
                comment_text = comment_item.get('content', '')
                user_nickname = comment_item.get('user', '匿名用户')
                user_rating = comment_item.get('rating', '0')
                comment_time = comment_item.get('time', None)
            else:
                # 旧格式的评论，纯文本字符串
                if not isinstance(comment_item, str) or not comment_item.strip():
                    continue
                
                comment_text = comment_item
                user_nickname = None
                user_rating = None
                comment_time = None
                
            # 文本清洗
            cleaned_text = TextProcessor.clean_text(comment_text)
            
            # 情感分析
            sentiment, sentiment_score = TextProcessor.analyze_sentiment(cleaned_text)
            
            # 创建评论对象
            comment_data = {
                'movie_id': movie_id,
                'content': cleaned_text,
                'sentiment': sentiment,
                'sentiment_score': sentiment_score,
                'user_nickname': user_nickname,
                'user_rating': user_rating,
                'comment_time': comment_time,
                'keywords': TextProcessor.extract_keywords(cleaned_text, top_n=5),
                'comment_strategy': comment_strategy  # 添加策略信息
            }
            
            processed_comments.append(comment_data)
            
            # 添加到缓冲区
            self.comment_buffer.append(comment_data)
            
            # 如果缓冲区达到批量大小，则批量插入
            if len(self.comment_buffer) >= self.batch_size:
                self._flush_buffer(spider)
                
        spider.logger.info(f"CommentPipeline: 纯文本评论处理完成，电影ID: {movie_id}, 处理评论数: {len(processed_comments)}")
    
    def _flush_buffer(self, spider):
        """批量插入评论缓冲区中的数据"""
        if not self.comment_buffer:
            return
            
        try:
            # 批量插入到MongoDB
            if self.mongo_client:
                result_ids = self.mongo_client.insert_many_comments(self.comment_buffer)
                spider.logger.info(f"CommentPipeline: 批量插入评论成功，数量: {len(result_ids)}")
                
            # 清空缓冲区
            self.comment_buffer = []
            
        except Exception as e:
            spider.logger.error(f"CommentPipeline: 批量插入评论失败: {str(e)}")
    
    def close_spider(self, spider):
        """爬虫关闭时，处理剩余的评论并关闭连接"""
        if spider.name != 'douban_spider':
            return
            
        try:
            # 处理缓冲区中剩余的评论
            if self.comment_buffer:
                self._flush_buffer(spider)
                
            spider.logger.info("CommentPipeline: 爬虫关闭，评论处理完成")
            
        except Exception as e:
            spider.logger.error(f"CommentPipeline: 关闭时出错: {str(e)}")
        
        # 不主动关闭MongoDB连接，因为它是单例模式并可能被其他组件使用