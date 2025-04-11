import logging
import pymongo
from pymongo import ASCENDING, DESCENDING
from django.conf import settings
import datetime
from typing import List, Dict, Any, Tuple, Optional, Union
from bson.objectid import ObjectId
import json
import jieba
import importlib

logger = logging.getLogger(__name__)

# 延迟导入jieba
_jieba = None

def get_jieba():
    """延迟加载jieba模块"""
    global _jieba
    if _jieba is None:
        import jieba
        _jieba = jieba
    return _jieba

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
            self.db_name = mongo_settings['db']  # 存储数据库名称
            self.comments_collection = self.db[mongo_settings['collection']]
            
            # 记录配置信息
            logger.info(f"MongoDB配置: 数据库={mongo_settings['db']}, 集合={mongo_settings['collection']}")
            
            # 测试连接
            self.client.admin.command('ping')
            logger.info(f"MongoDB连接成功: {self.client.address}")
            
            # 创建索引
            self._create_indexes()
            
            self._initialized = True
            logger.info("MongoDB客户端初始化成功")
            
        except Exception as e:
            logger.error(f"MongoDB客户端初始化失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
            comment_data['created_at'] = datetime.datetime.now()
            
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
                comment['created_at'] = datetime.datetime.now()
            
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
                if 'comment_time' in doc and isinstance(doc['comment_time'], datetime.datetime):
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
                if 'comment_time' in doc and isinstance(doc['comment_time'], datetime.datetime):
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
                if 'comment_time' in doc and isinstance(doc['comment_time'], datetime.datetime):
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
                if 'comment_time' in doc and isinstance(doc['comment_time'], datetime.datetime):
                    doc['comment_time'] = doc['comment_time'].strftime('%Y-%m-%d %H:%M:%S')
                comments.append(doc)
                
            return comments, total
        except Exception as e:
            logger.error(f"搜索评论失败: {str(e)}")
            return [], 0
    
    def get_comment_keywords(self, movie_id):
        """获取电影评论关键词，用于生成词云"""
        try:
            # 先从comments_collection中直接获取关键词
            # 聚合查询，统计所有评论中的关键词
            pipeline = [
                {"$match": {"movie_id": int(movie_id)}},
                {"$unwind": "$keywords"},
                {"$group": {
                    "_id": "$keywords",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 100}  # 限制返回100个最常见的关键词
            ]
            
            result = list(self.comments_collection.aggregate(pipeline))
            
            if result and len(result) > 0:
                # 转换为符合词云格式的数据
                keywords = []
                for item in result:
                    if item["_id"] and item["count"]:
                        keywords.append({
                            "name": str(item["_id"]),
                            "value": int(item["count"])
                        })
                
                logging.info(f"从评论集合中直接获取到 {movie_id} 的关键词: {len(keywords)} 个")
                return keywords
            
            # 如果直接从评论中获取失败，尝试从其他集合获取
            db = self.client[self.db_name]
            collection = db['comment_keywords']
            
            # 获取关键词数据
            result = collection.find_one({'movie_id': str(movie_id)})
            
            if result and 'keywords' in result:
                logging.info(f"获取到电影 {movie_id} 的评论关键词: {len(result['keywords'])} 个")
                
                # 确保数据格式正确
                keywords = []
                if isinstance(result['keywords'], list):
                    # 如果是字符串列表，转换为适合词云的格式
                    word_count = {}
                    for word in result['keywords']:
                        if word in word_count:
                            word_count[word] += 1
                        else:
                            word_count[word] = 1
                    
                    # 转换为词云需要的格式
                    for word, count in word_count.items():
                        keywords.append({
                            'name': str(word),
                            'value': count
                        })
                elif isinstance(result['keywords'], dict):
                    # 如果已经是词频统计字典
                    for word, count in result['keywords'].items():
                        keywords.append({
                            'name': str(word),
                            'value': count
                        })
                
                logging.info(f"格式化后的关键词: {len(keywords)} 个")
                return keywords
            else:
                logging.warning(f"电影 {movie_id} 的评论关键词数据不存在或格式不正确")
                # 尝试从其他集合中获取数据
                return self.get_wordcloud_data(movie_id)
                
        except Exception as e:
            logging.error(f"获取电影评论关键词失败: {str(e)}", exc_info=True)
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
    
    def get_wordcloud_data_by_strategy(self, movie_id, strategy):
        """获取指定采集策略的词云数据"""
        try:
            # 构建策略查询条件
            strategy_mapping = {
                'sequential': ["顺序采集", "sequential", "顺序策略"],
                'random_pages': ["随机页码采集", "random_pages", "随机页码策略"],
                'random_interval': ["随机间隔采集", "random_interval", "随机间隔策略"],
                'random_block': ["随机区块采集", "random_block", "随机区块策略"],
                'random_select': ["随机选择采集", "random_select", "随机选择策略"]
            }
            
            # 获取策略对应的所有可能值
            strategy_values = strategy_mapping.get(strategy, [strategy])
            
            # 构建查询条件 - 支持部分匹配
            query_conditions = []
            for value in strategy_values:
                query_conditions.append({"comment_strategy": {"$regex": value, "$options": "i"}})
            
            # 聚合查询，按指定策略查找评论关键词
            pipeline = [
                {"$match": {
                    "movie_id": int(movie_id),
                    "$or": query_conditions
                }},
                {"$unwind": "$keywords"},
                {"$group": {
                    "_id": "$keywords",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 100}  # 限制返回100个最常见的关键词
            ]
            
            result = list(self.comments_collection.aggregate(pipeline))
            
            if result and len(result) > 0:
                # 转换为符合词云格式的数据
                formatted_data = []
                for item in result:
                    if item["_id"] and item["count"]:
                        formatted_data.append({
                            "name": str(item["_id"]),
                            "value": int(item["count"])
                        })
                
                logging.info(f"获取到策略 '{strategy}' 的词云数据: {len(formatted_data)} 个关键词")
                return formatted_data
            
            # 如果从评论集合中获取失败，尝试从专门的策略词云集合获取
            db = self.client[self.db_name]
            collection = db['strategy_wordcloud']
            
            # 查询对应策略的数据
            result = collection.find_one({
                'movie_id': str(movie_id),
                'strategy': strategy
            })
            
            if result and 'wordcloud' in result and result['wordcloud']:
                data = result['wordcloud']
                logging.info(f"从策略词云集合找到电影 {movie_id} 的 {strategy} 策略词云数据: {len(data)} 项")
                
                # 标准化数据格式
                formatted_data = []
                for item in data:
                    if isinstance(item, dict):
                        word = item.get('word', item.get('name', item.get('keyword', '')))
                        weight = item.get('weight', item.get('value', item.get('count', 1)))
                        
                        if word:
                            formatted_data.append({
                                'name': str(word),
                                'value': float(weight) if isinstance(weight, (int, float)) else 1
                            })
                    elif isinstance(item, list) and len(item) >= 2:
                        formatted_data.append({
                            'name': str(item[0]),
                            'value': float(item[1]) if isinstance(item[1], (int, float)) else 1
                        })
                
                # 过滤和排序
                formatted_data = [item for item in formatted_data if item['name'] and item['name'].strip()]
                formatted_data.sort(key=lambda x: x['value'], reverse=True)
                
                # 限制返回数量
                max_items = 100
                if len(formatted_data) > max_items:
                    formatted_data = formatted_data[:max_items]
                    
                return formatted_data
            
            # 如果找不到特定策略的数据，尝试从评论中生成
            return self.generate_strategy_wordcloud(movie_id, strategy)
            
        except Exception as e:
            logging.error(f"获取策略词云数据失败 ({strategy}): {str(e)}", exc_info=True)
            return []
    
    def generate_strategy_wordcloud(self, movie_id, strategy, limit=100):
        """
        如果数据库中不存在，则根据评论采集策略生成词云数据
        
        Args:
            movie_id: 电影ID
            strategy: 采集策略名称 ('sequential', 'random_pages', 'random_interval', 'random_block')
            limit: 返回的关键词数量上限
        
        Returns:
            适用于ECharts词云图的数据列表
        """
        try:
            logging.info(f"尝试为电影 {movie_id} 的 {strategy} 策略生成词云数据")
            
            # 构建策略查询条件
            strategy_mapping = {
                'sequential': ["顺序采集", "sequential", "顺序策略"],
                'random_pages': ["随机页码采集", "random_pages", "随机页码策略"],
                'random_interval': ["随机间隔采集", "random_interval", "随机间隔策略"],
                'random_block': ["随机区块采集", "random_block", "随机区块策略"]
            }
            
            # 获取策略对应的所有可能值
            strategy_values = strategy_mapping.get(strategy, [strategy])
            
            # 构建查询条件 - 支持部分匹配
            query_conditions = []
            for value in strategy_values:
                query_conditions.append({"comment_strategy": {"$regex": value, "$options": "i"}})
            
            # 查询符合策略的评论
            comments = list(self.comments_collection.find({
                "movie_id": int(movie_id),
                "$or": query_conditions
            }))
            
            logging.info(f"找到策略 '{strategy}' 下的评论: {len(comments)} 条")
            
            # 如果没有找到评论，返回空列表
            if not comments or len(comments) == 0:
                logging.warning(f"电影 {movie_id} 的 {strategy} 策略没有评论数据")
                return []
            
            # 提取所有关键词
            keyword_count = {}
            for comment in comments:
                if 'keywords' in comment:
                    if isinstance(comment['keywords'], list):
                        for keyword in comment['keywords']:
                            if keyword in keyword_count:
                                keyword_count[keyword] += 1
                            else:
                                keyword_count[keyword] = 1
                    elif isinstance(comment['keywords'], str):
                        if comment['keywords'] in keyword_count:
                            keyword_count[comment['keywords']] += 1
                        else:
                            keyword_count[comment['keywords']] = 1
            
            if not keyword_count:
                logging.warning(f"电影 {movie_id} 的 {strategy} 策略评论没有关键词")
                return []
            
            # 转换为词云数据格式
            wordcloud_data = []
            for keyword, count in keyword_count.items():
                if keyword and keyword.strip():
                    wordcloud_data.append({
                        "name": str(keyword),
                        "value": count
                    })
            
            # 排序并限制数量
            wordcloud_data.sort(key=lambda x: x["value"], reverse=True)
            if len(wordcloud_data) > limit:
                wordcloud_data = wordcloud_data[:limit]
            
            logging.info(f"成功生成词云数据，共 {len(wordcloud_data)} 个关键词")
            
            # 保存生成的词云数据到数据库
            try:
                # 确保策略词云集合存在
                if 'strategy_wordcloud' not in self.db.list_collection_names():
                    self.db.create_collection('strategy_wordcloud')
                
                strategy_collection = self.db['strategy_wordcloud']
                strategy_collection.update_one(
                    {"movie_id": str(movie_id), "strategy": strategy},
                    {"$set": {
                        "wordcloud": wordcloud_data,
                        "generated_at": datetime.datetime.now()
                    }},
                    upsert=True
                )
                logging.info(f"已将词云数据保存到数据库")
            except Exception as e:
                logging.error(f"保存词云数据失败: {str(e)}")
            
            return wordcloud_data
            
        except Exception as e:
            logging.error(f"生成策略词云数据失败: {str(e)}", exc_info=True)
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
            archive_date = datetime.datetime.now() - datetime.timedelta(days=days)
            
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
            start_date = datetime.datetime.now() - datetime.timedelta(days=days)
            
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
    
    def get_wordcloud_data(self, movie_id):
        """获取电影词云数据，如果不存在则生成"""
        try:
            # 先从wordcloud_collection中获取数据
            db = self.client[self.db_name]
            collection = db['wordcloud']
            
            # 获取词云数据
            result = collection.find_one({'movie_id': str(movie_id)})
            
            if result and 'data' in result:
                logging.info(f"获取到电影 {movie_id} 的词云数据: {len(result['data'])} 个词")
                return result['data']
            
            # 如果词云数据不存在，尝试从评论中生成
            logging.info(f"电影 {movie_id} 的词云数据不存在，尝试从评论中生成")
            
            # 获取电影评论
            comments = self.get_movie_comments(movie_id)
            if not comments:
                logging.warning(f"电影 {movie_id} 没有评论数据")
                return []
            
            # 提取评论文本
            comment_texts = []
            for comment in comments:
                if 'content' in comment:
                    comment_texts.append(comment['content'])
            
            if not comment_texts:
                logging.warning(f"电影 {movie_id} 的评论内容为空")
                return []
            
            # 合并所有评论文本
            text = ' '.join(comment_texts)
            
            # 使用jieba进行分词
            jieba = self._get_jieba()
            words = jieba.analyse.extract_tags(text, topK=100, withWeight=True)
            
            # 转换为词云需要的格式
            wordcloud_data = []
            for word, weight in words:
                wordcloud_data.append({
                    'name': word,
                    'value': int(weight * 1000)  # 将权重转换为整数
                })
            
            # 保存词云数据
            collection.insert_one({
                'movie_id': str(movie_id),
                'data': wordcloud_data,
                'update_time': datetime.now()
            })
            
            logging.info(f"生成并保存了电影 {movie_id} 的词云数据: {len(wordcloud_data)} 个词")
            return wordcloud_data
            
        except Exception as e:
            logging.error(f"获取电影词云数据失败: {str(e)}", exc_info=True)
            return []

    def _get_jieba(self):
        """动态导入jieba模块"""
        if self._jieba is None:
            try:
                self._jieba = importlib.import_module('jieba')
            except ImportError as e:
                logger.error(f"导入jieba模块失败: {str(e)}")
                raise
        return self._jieba

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
    wordcloud_data = client.get_comment_keywords(test_movie_id)
    
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

    # 测试获取不同策略的词云数据
    print("\n测试获取不同策略的词云数据...")
    strategies = ['sequential', 'random_pages', 'random_interval', 'random_block']

    for strategy in strategies:
        print(f"\n测试获取 '{strategy}' 策略的词云数据...")
        strategy_wordcloud = client.get_wordcloud_data_by_strategy(test_movie_id, strategy)

        if strategy_wordcloud:
            print(f"成功获取 '{strategy}' 策略词云数据，共 {len(strategy_wordcloud)} 个关键词")
            # 打印前3个关键词
            for i, item in enumerate(strategy_wordcloud[:3]):
                print(f"关键词 {i+1}: {item['name']} (权重: {item['value']})")
        else:
            print(f"未获取到 '{strategy}' 策略的词云数据")
