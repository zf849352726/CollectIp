import pymongo
from pymongo import ASCENDING, DESCENDING
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
from django.conf import settings
from bson.objectid import ObjectId
import json

logger = logging.getLogger(__name__)

class MongoDBClient:
    """MongoDB客户端单例类"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        try:
            # 获取MongoDB配置
            mongo_settings = settings.MONGODB_CONN
            
            # 构建连接URI
            uri = f"mongodb://{mongo_settings['host']}:{mongo_settings['port']}"
            if mongo_settings.get('username') and mongo_settings.get('password'):
                uri = f"mongodb://{mongo_settings['username']}:{mongo_settings['password']}@{mongo_settings['host']}:{mongo_settings['port']}"
            
            # 创建MongoDB客户端
            self.client = pymongo.MongoClient(uri)
            
            # 获取数据库和集合
            self.db = self.client[mongo_settings['db']]
            self.comments_collection = self.db[mongo_settings['collection']]
            
            # 创建索引
            self._create_indexes()
            
            self._initialized = True
            logger.info("MongoDB客户端初始化成功")
            
        except Exception as e:
            logger.error(f"MongoDB客户端初始化失败: {str(e)}")
            raise
    
    def _create_indexes(self):
        """创建必要的索引"""
        try:
            # 创建电影ID索引
            self.comments_collection.create_index([("movie_id", ASCENDING)])
            
            # 创建评论时间索引
            self.comments_collection.create_index([("comment_time", DESCENDING)])
            
            # 创建情感分析索引
            self.comments_collection.create_index([("sentiment", ASCENDING)])
            
            # 创建用户评分索引
            self.comments_collection.create_index([("user_rating", ASCENDING)])
            
            # 创建文本搜索索引
            self.comments_collection.create_index([("content", "text")])
            
            logger.info("MongoDB索引创建成功")
        except Exception as e:
            logger.error(f"MongoDB索引创建失败: {str(e)}")
    
    @classmethod
    def get_instance(cls):
        """获取MongoDB客户端实例"""
        return cls()
    
    def insert_comment(self, comment_data):
        """插入单条评论数据"""
        try:
            # 确保movie_id是整数类型
            if 'movie_id' in comment_data and comment_data['movie_id'] is not None:
                comment_data['movie_id'] = int(comment_data['movie_id'])
            
            # 添加创建时间
            comment_data['created_at'] = datetime.now()
            
            # 插入评论
            result = self.comments_collection.insert_one(comment_data)
            return result.inserted_id
        except Exception as e:
            logger.error(f"插入评论失败: {str(e)}")
            return None
    
    def insert_many_comments(self, comments_data):
        """批量插入多条评论数据"""
        if not comments_data:
            return []
            
        try:
            # 确保所有评论的movie_id是整数类型，并添加创建时间
            for comment in comments_data:
                if 'movie_id' in comment and comment['movie_id'] is not None:
                    comment['movie_id'] = int(comment['movie_id'])
                comment['created_at'] = datetime.now()
            
            # 批量插入
            result = self.comments_collection.insert_many(comments_data)
            return result.inserted_ids
        except Exception as e:
            logger.error(f"批量插入评论失败: {str(e)}")
            return []
    
    def get_comments_by_movie_id(self, movie_id, limit=20, skip=0, sort_by=None):
        """根据电影ID获取评论"""
        try:
            if sort_by is None:
                sort_by = [("comment_time", DESCENDING), ("created_at", DESCENDING)]
                
            # 查询指定电影的评论
            cursor = self.comments_collection.find(
                {"movie_id": int(movie_id)}
            ).sort(sort_by).skip(skip).limit(limit)
            
            # 计算总数
            total = self.comments_collection.count_documents({"movie_id": int(movie_id)})
            
            # 转换ObjectId为字符串
            comments = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                if 'created_at' in doc:
                    doc['created_at'] = doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if 'comment_time' in doc and isinstance(doc['comment_time'], datetime):
                    doc['comment_time'] = doc['comment_time'].strftime('%Y-%m-%d %H:%M:%S')
                comments.append(doc)
                
            return comments, total
        except Exception as e:
            logger.error(f"获取电影评论失败: {str(e)}")
            return [], 0
    
    def get_comments_by_rating(self, movie_id, rating, limit=20, skip=0):
        """根据评分获取电影评论"""
        try:
            # 查询指定电影的指定评分评论
            cursor = self.comments_collection.find({
                "movie_id": int(movie_id),
                "user_rating": str(rating)
            }).sort([("comment_time", DESCENDING)]).skip(skip).limit(limit)
            
            # 计算总数
            total = self.comments_collection.count_documents({
                "movie_id": int(movie_id),
                "user_rating": str(rating)
            })
            
            # 转换数据
            comments = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                if 'created_at' in doc:
                    doc['created_at'] = doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if 'comment_time' in doc and isinstance(doc['comment_time'], datetime):
                    doc['comment_time'] = doc['comment_time'].strftime('%Y-%m-%d %H:%M:%S')
                comments.append(doc)
                
            return comments, total
        except Exception as e:
            logger.error(f"获取评论失败: {str(e)}")
            return [], 0
    
    def get_comments_by_sentiment(self, movie_id, sentiment, limit=20, skip=0):
        """获取指定情感倾向的评论"""
        try:
            # 查询指定电影的指定情感评论
            cursor = self.comments_collection.find({
                "movie_id": int(movie_id),
                "sentiment": sentiment
            }).sort([("comment_time", DESCENDING)]).skip(skip).limit(limit)
            
            # 计算总数
            total = self.comments_collection.count_documents({
                "movie_id": int(movie_id),
                "sentiment": sentiment
            })
            
            # 转换ObjectId为字符串
            comments = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                if 'created_at' in doc:
                    doc['created_at'] = doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if 'comment_time' in doc and isinstance(doc['comment_time'], datetime):
                    doc['comment_time'] = doc['comment_time'].strftime('%Y-%m-%d %H:%M:%S')
                comments.append(doc)
                
            return comments, total
        except Exception as e:
            logger.error(f"获取情感评论失败: {str(e)}")
            return [], 0
    
    def search_comments(self, movie_id, keyword, limit=20, skip=0):
        """搜索评论内容"""
        try:
            # 创建文本索引（如果不存在）
            self.comments_collection.create_index([("content", "text")])
            
            # 执行文本搜索
            cursor = self.comments_collection.find({
                "movie_id": int(movie_id),
                "$text": {"$search": keyword}
            }).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(limit)
            
            # 计算总数
            total = self.comments_collection.count_documents({
                "movie_id": int(movie_id),
                "$text": {"$search": keyword}
            })
            
            # 转换数据
            comments = []
            for doc in cursor:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
                if 'created_at' in doc:
                    doc['created_at'] = doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                if 'comment_time' in doc and isinstance(doc['comment_time'], datetime):
                    doc['comment_time'] = doc['comment_time'].strftime('%Y-%m-%d %H:%M:%S')
                comments.append(doc)
                
            return comments, total
        except Exception as e:
            logger.error(f"搜索评论失败: {str(e)}")
            return [], 0
    
    def get_comment_keywords(self, movie_id, limit=10):
        """获取电影评论的热门关键词"""
        try:
            # 聚合查询，展开keywords数组并计数
            pipeline = [
                {"$match": {"movie_id": int(movie_id)}},
                {"$unwind": "$keywords"},
                {"$group": {
                    "_id": "$keywords",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            
            result = list(self.comments_collection.aggregate(pipeline))
            
            # 转换为前端需要的格式
            keywords = [{"name": item["_id"], "value": item["count"]} for item in result]
            return keywords
        except Exception as e:
            logger.error(f"获取评论关键词失败: {str(e)}")
            return []
    
    def get_sentiment_stats(self, movie_id):
        """获取电影评论情感统计"""
        try:
            # 聚合查询，统计各情感评论数量
            pipeline = [
                {"$match": {"movie_id": int(movie_id)}},
                {"$group": {
                    "_id": "$sentiment",
                    "count": {"$sum": 1}
                }}
            ]
            
            result = list(self.comments_collection.aggregate(pipeline))
            
            # 整理统计结果
            stats = {
                "positive": 0,  # 正面
                "neutral": 0,   # 中性
                "negative": 0,  # 负面
                "total": 0      # 总数
            }
            
            for item in result:
                sentiment = item["_id"]
                count = item["count"]
                stats["total"] += count
                
                if sentiment == 1:
                    stats["positive"] = count
                elif sentiment == 0:
                    stats["neutral"] = count
                elif sentiment == -1:
                    stats["negative"] = count
            
            return stats
        except Exception as e:
            logger.error(f"获取评论情感统计失败: {str(e)}")
            return {
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "total": 0
            }
    
    def get_rating_stats(self, movie_id):
        """获取电影评分统计"""
        try:
            # 聚合查询，统计各评分数量
            pipeline = [
                {"$match": {"movie_id": int(movie_id)}},
                {"$group": {
                    "_id": "$user_rating",
                    "count": {"$sum": 1}
                }}
            ]
            
            result = list(self.comments_collection.aggregate(pipeline))
            
            # 整理统计结果
            stats = {
                "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, 
                "total": 0, "avg": 0
            }
            
            total_score = 0
            total_count = 0
            
            for item in result:
                rating = item["_id"]
                count = item["count"]
                
                if rating in ["1", "2", "3", "4", "5"]:
                    stats[rating] = count
                    total_score += int(rating) * count
                    total_count += count
            
            stats["total"] = total_count
            
            # 计算平均评分
            if total_count > 0:
                stats["avg"] = round(total_score / total_count, 1)
            
            return stats
        except Exception as e:
            logger.error(f"获取评分统计失败: {str(e)}")
            return {
                "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, 
                "total": 0, "avg": 0
            }
    
    def get_wordcloud_data(self, movie_id, limit=100):
        """生成词云数据"""
        try:
            # 先获取评论内容
            comments, _ = self.get_comments_by_movie_id(movie_id, limit=300)
            
            if not comments:
                return []
                
            # 导入TextProcessor
            from index.text_utils import TextProcessor
            
            # 提取评论内容
            comment_texts = [comment.get('content', '') for comment in comments if comment.get('content')]
            
            # 生成词云数据
            word_cloud_data = TextProcessor.generate_wordcloud_data(comment_texts, top_n=limit)
            
            return word_cloud_data
        except Exception as e:
            logger.error(f"生成词云数据失败: {str(e)}")
            return []
    
    def delete_comments_by_movie_id(self, movie_id):
        """删除指定电影的所有评论"""
        try:
            result = self.comments_collection.delete_many({"movie_id": int(movie_id)})
            return result.deleted_count
        except Exception as e:
            logger.error(f"删除电影评论失败: {str(e)}")
            return 0
    
    def close(self):
        """关闭MongoDB连接"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            self.comments_collection = None
    
    def archive_old_comments(self, days: int = 365):
        """归档旧评论"""
        try:
            # 计算归档时间点
            archive_date = datetime.now() - timedelta(days=days)
            
            # 创建归档集合
            archive_collection = self.db[f"{self.comments_collection.name}_archive"]
            
            # 查找并移动旧评论
            old_comments = self.comments_collection.find({
                "comment_time": {"$lt": archive_date}
            })
            
            if old_comments:
                archive_collection.insert_many(old_comments)
                self.comments_collection.delete_many({
                    "comment_time": {"$lt": archive_date}
                })
                
            logger.info(f"成功归档{days}天前的评论")
            
        except Exception as e:
            logger.error(f"归档评论失败: {str(e)}")
    
    def sample_comments(self, movie_id: int, sample_size: int = 1000) -> List[Dict]:
        """对热门电影的评论进行采样"""
        try:
            # 使用聚合管道进行随机采样
            pipeline = [
                {"$match": {"movie_id": movie_id}},
                {"$sample": {"size": sample_size}}
            ]
            
            return list(self.comments_collection.aggregate(pipeline))
            
        except Exception as e:
            logger.error(f"评论采样失败: {str(e)}")
            return []
    
    def get_hot_movies(self, limit: int = 10) -> List[Dict]:
        """获取热门电影（评论数量最多的电影）"""
        try:
            pipeline = [
                {"$group": {
                    "_id": "$movie_id",
                    "comment_count": {"$sum": 1},
                    "avg_sentiment": {"$avg": "$sentiment_score"},
                    "avg_rating": {"$avg": {"$toDouble": "$user_rating"}}
                }},
                {"$sort": {"comment_count": -1}},
                {"$limit": limit}
            ]
            
            return list(self.comments_collection.aggregate(pipeline))
            
        except Exception as e:
            logger.error(f"获取热门电影失败: {str(e)}")
            return []
    
    def get_comment_trends(self, movie_id: int, days: int = 30) -> List[Dict]:
        """获取评论趋势数据"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            pipeline = [
                {"$match": {
                    "movie_id": movie_id,
                    "comment_time": {"$gte": start_date}
                }},
                {"$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$comment_time"
                        }
                    },
                    "count": {"$sum": 1},
                    "avg_sentiment": {"$avg": "$sentiment_score"},
                    "avg_rating": {"$avg": {"$toDouble": "$user_rating"}}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            return list(self.comments_collection.aggregate(pipeline))
            
        except Exception as e:
            logger.error(f"获取评论趋势失败: {str(e)}")
            return []
    
    def get_wordcloud_data_by_strategy(self, movie_id, strategy, limit=100):
        """
        根据评论采集策略获取词云数据
        
        Args:
            movie_id: 电影ID
            strategy: 采集策略名称 ('sequential', 'random_pages', 'random_interval', 'random_block')
            limit: 返回的关键词数量上限
            
        Returns:
            适用于ECharts词云图的数据列表
        """
        try:
            # 连接到MongoDB
            collection = self.comments_collection
            
            # 尝试将movie_id转换为整数（如果可能）
            try:
                movie_id_int = int(movie_id)
            except (ValueError, TypeError):
                movie_id_int = None
                
            # 构建查询条件
            match_condition = {"$or": []}
            
            # 添加电影ID条件（支持字符串和整数两种格式）
            if movie_id_int is not None:
                match_condition["$or"].append({"movie_id": movie_id_int})
            match_condition["$or"].append({"movie_id": str(movie_id)})
            
            # 构建策略匹配条件
            if strategy == 'sequential':
                # 顺序策略可能存储为顺序策略、顺序采集或空值/缺失
                strategy_condition = {"$or": [
                    {"comment_strategy": "顺序策略"},
                    {"comment_strategy": "sequential"},
                    {"comment_strategy": "顺序采集"},
                    {"comment_strategy": {"$exists": False}},
                    {"comment_strategy": None}
                ]}
            else:
                strategy_name_mappings = {
                    'random_pages': ["随机页码策略", "random_pages"],
                    'random_interval': ["随机间隔策略", "random_interval"],
                    'random_block': ["随机区块策略", "random_block"]
                }
                
                strategy_names = strategy_name_mappings.get(strategy, [strategy])
                strategy_condition = {"comment_strategy": {"$in": strategy_names}}
            
            # 合并查询条件
            query = {"$and": [match_condition, strategy_condition]}
            
            # 记录查询条件
            self.logger.info(f"策略词云查询条件: {query}")
            
            # 查询评论数据
            cursor = collection.find(query, {"content": 1})
            comments = list(cursor)
            
            # 记录找到的评论数量
            self.logger.info(f"找到策略 '{strategy}' 下的评论: {len(comments)} 条")
            
            # 如果没有找到评论数据，返回空列表
            if not comments:
                return []
            
            # 合并所有评论内容
            all_text = " ".join([comment.get("content", "") for comment in comments if comment.get("content")])
            
            # 使用文本处理工具提取关键词
            from index.text_utils import TextProcessor
            text_processor = TextProcessor()
            keywords = text_processor.extract_keywords(all_text, top_k=limit)
            
            # 构造词云数据
            wordcloud_data = []
            for word, weight in keywords:
                wordcloud_data.append({
                    "name": word,
                    "value": weight * 1000  # 放大权重值以便在词云中更好地显示
                })
            
            return wordcloud_data
            
        except Exception as e:
            logger.error(f"获取策略词云数据失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []

if __name__ == "__main__":
    # 测试MongoDB连接和词云生成功能
    import os
    import django
    
    # 如果找不到模块，尝试调整路径
    import sys
    from pathlib import Path
    
    # 获取当前文件所在目录
    current_dir = Path(__file__).resolve().parent
    # 获取项目根目录（假设index是项目下的一个应用）
    BASE_DIR = current_dir.parent
    
    # 添加项目根目录到Python路径
    sys.path.insert(0, str(BASE_DIR))
    
    # 设置Django设置模块
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')
    # 或者尝试
    # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
    
    # 初始化Django
    django.setup()
    
    client = MongoDBClient.get_instance()
    
    # 测试获取词云数据
    test_movie_name = "霸王别姬"  # 这里使用一个示例电影名称，可以根据实际情况修改
    from index.models import Movie
    try:
        movie = Movie.objects.get(title=test_movie_name)
        test_movie_id = movie.id
        print(f"测试获取电影《{test_movie_name}》(ID: {test_movie_id})的词云数据...")
    except Movie.DoesNotExist:
        print(f"电影《{test_movie_name}》不存在，使用默认ID")
        test_movie_id = 1291543
        print(f"测试获取电影ID {test_movie_id} 的词云数据...")
    except Exception as e:
        print(f"查询电影时出错: {str(e)}，使用默认ID")
        test_movie_id = 1291543
        print(f"测试获取电影ID {test_movie_id} 的词云数据...")
    
    # 获取词云数据
    wordcloud_data = client.get_wordcloud_data(test_movie_id)
    
    if wordcloud_data:
        print(f"成功获取词云数据，共 {len(wordcloud_data)} 个关键词")
        # 打印前5个关键词
        for i, item in enumerate(wordcloud_data[:5]):
            print(f"关键词 {i+1}: {item['name']} (权重: {item['value']})")
    else:
        print("未获取到词云数据，请检查以下可能的原因：")
        print("1. 数据库中是否存在该电影的评论")
        print("2. MongoDB连接是否正常")
        print("3. 评论数据格式是否正确")
    
    # 测试获取评论关键词
    print("\n测试获取评论关键词...")
    keywords = client.get_comment_keywords(test_movie_id)
    if keywords:
        print(f"成功获取评论关键词，共 {len(keywords)} 个")
        print(f"前5个关键词: {keywords[:5]}")
    else:
        print("未获取到评论关键词")
