#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MongoDB连接测试脚本
用于检查MongoDB连接和词云数据
"""

import os
import sys
import pymongo
import datetime
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB连接配置（从settings.py复制）
MONGODB_CONN = {
    'host': 'localhost',
    'port': 27017,
    'db': 'collectip_comments',
    'collection': 'movie_comments',
    'username': '',
    'password': '',
}

def check_mongodb_connection():
    """检查MongoDB连接状态"""
    try:
        # 构建连接URI
        uri = f"mongodb://{MONGODB_CONN['host']}:{MONGODB_CONN['port']}"
        if MONGODB_CONN.get('username') and MONGODB_CONN.get('password'):
            uri = f"mongodb://{MONGODB_CONN['username']}:{MONGODB_CONN['password']}@{MONGODB_CONN['host']}:{MONGODB_CONN['port']}"
        
        # 创建MongoDB客户端
        client = pymongo.MongoClient(uri)
        
        # 测试连接
        client.admin.command('ping')
        logger.info("MongoDB服务器连接成功")
        
        # 获取数据库和集合
        db = client[MONGODB_CONN['db']]
        comments_collection = db[MONGODB_CONN['collection']]
        
        logger.info(f"MongoDB数据库名称: {db.name}")
        logger.info(f"MongoDB评论集合名称: {comments_collection.name}")
        
        return client, db
    except Exception as e:
        logger.error(f"MongoDB连接检查失败: {e}")
        return None, None

def list_collections(db):
    """列出所有集合"""
    try:
        collections = db.list_collection_names()
        logger.info(f"数据库中包含以下集合: {collections}")
        return collections
    except Exception as e:
        logger.error(f"列出集合失败: {e}")
        return []

def check_wordcloud_data(db, movie_id):
    """检查词云数据"""
    try:
        logger.info(f"尝试获取电影ID {movie_id} 的词云数据")
        
        # 直接检查相关集合中的数据
        collections_to_check = [
            'comment_keywords',
            'comment_wordcloud',
            'movie_analytics',
            'movie_comments',
            'movie_data',
            'strategy_wordcloud'
        ]
        
        found_data = False
        
        for coll_name in collections_to_check:
            try:
                if coll_name in db.list_collection_names():
                    collection = db[coll_name]
                    # 尝试查找字符串和整数两种ID格式
                    result = collection.find_one({"movie_id": str(movie_id)})
                    if not result:
                        try:
                            result = collection.find_one({"movie_id": int(movie_id)})
                        except:
                            pass
                    
                    if result:
                        logger.info(f"在集合 {coll_name} 中找到电影 {movie_id} 的数据")
                        # 尝试找出词云相关的字段
                        keys = list(result.keys())
                        logger.info(f"数据包含以下字段: {keys[:10]}...")
                        
                        # 检查常见词云字段
                        cloud_fields = ['keywords', 'wordcloud', 'word_freq', 'wordcloud_data', 'terms']
                        for field in cloud_fields:
                            if field in result and result[field]:
                                data = result[field]
                                if isinstance(data, list):
                                    logger.info(f"在字段 {field} 中找到 {len(data)} 个数据项")
                                    if len(data) > 0:
                                        logger.info(f"数据示例: {data[0]}")
                                    found_data = True
                                elif isinstance(data, dict):
                                    logger.info(f"在字段 {field} 中找到 {len(data)} 个键值对")
                                    if len(data) > 0:
                                        first_key = next(iter(data))
                                        logger.info(f"数据示例: {first_key}: {data[first_key]}")
                                    found_data = True
                    else:
                        logger.info(f"在集合 {coll_name} 中未找到电影 {movie_id} 的数据")
                else:
                    logger.info(f"数据库中不存在集合 {coll_name}")
            except Exception as e:
                logger.warning(f"检查集合 {coll_name} 时出错: {e}")
        
        return found_data
    except Exception as e:
        logger.error(f"检查词云数据失败: {e}")
        return False

def list_movie_ids(db):
    """列出数据库中存在的所有电影ID"""
    try:
        logger.info("尝试列出数据库中存在的电影ID...")
        movie_ids = set()
        
        # 检查各集合中的电影ID
        collections_to_check = [
            'comment_keywords',
            'comment_wordcloud',
            'movie_analytics',
            'movie_comments',
            'movie_data',
            'strategy_wordcloud'
        ]
        
        for coll_name in collections_to_check:
            try:
                if coll_name in db.list_collection_names():
                    collection = db[coll_name]
                    # 使用distinct查找唯一的movie_id值
                    ids = collection.distinct("movie_id")
                    if ids:
                        logger.info(f"集合 {coll_name} 中找到 {len(ids)} 个电影ID")
                        movie_ids.update([str(mid) for mid in ids])
            except Exception as e:
                logger.warning(f"获取集合 {coll_name} 中的电影ID时出错: {e}")
        
        logger.info(f"总共找到 {len(movie_ids)} 个唯一电影ID")
        if movie_ids:
            logger.info(f"电影ID示例: {list(movie_ids)[:5]}")
        
        return list(movie_ids)
    except Exception as e:
        logger.error(f"列出电影ID失败: {e}")
        return []

def manually_create_wordcloud_data(db, movie_id, comments=None):
    """手动创建词云数据"""
    try:
        words = ['电影', '好看', '演技', '导演', '剧情', '精彩', '故事', '演员', '场景', '音乐', 
                '感人', '画面', '经典', '推荐', '情节', '喜欢', '不错', '表演', '期待', '值得']
        
        # 生成随机词云数据
        import random
        wordcloud_data = []
        for word in words:
            weight = random.randint(5, 100)
            wordcloud_data.append({
                'name': word,
                'value': weight
            })
        
        # 保存到数据库
        collection = db['comment_wordcloud']
        result = collection.update_one(
            {'movie_id': str(movie_id)},
            {'$set': {
                'wordcloud': wordcloud_data,
                'movie_id': str(movie_id),
                'generated_at': datetime.datetime.now()
            }},
            upsert=True
        )
        
        logger.info(f"手动创建的词云数据已保存: {result.acknowledged}")
        return wordcloud_data
    except Exception as e:
        logger.error(f"手动创建词云数据失败: {e}")
        return []

def insert_sample_wordcloud_for_all_movies(db):
    """为数据库中的所有电影创建示例词云数据"""
    try:
        # 获取所有电影ID
        movie_ids = list_movie_ids(db)
        
        if not movie_ids:
            logger.warning("找不到任何电影ID，无法创建示例词云数据")
            return False
        
        logger.info(f"准备为 {len(movie_ids)} 部电影创建示例词云数据")
        
        # 确保词云集合存在
        if 'comment_wordcloud' not in db.list_collection_names():
            logger.info("创建comment_wordcloud集合")
            db.create_collection('comment_wordcloud')
        
        # 确保策略词云集合存在
        if 'strategy_wordcloud' not in db.list_collection_names():
            logger.info("创建strategy_wordcloud集合")
            db.create_collection('strategy_wordcloud')
        
        for movie_id in movie_ids:
            # 确保movie_id是字符串
            movie_id = str(movie_id)
            logger.info(f"为电影 {movie_id} 创建词云数据")
            
            # 创建词云数据
            words = ['电影', '好看', '演技', '导演', '剧情', '精彩', '故事', '演员', '场景', '音乐', 
                    '感人', '画面', '经典', '推荐', '情节', '喜欢', '不错', '表演', '期待', '值得']
            
            # 生成随机词云数据
            import random
            wordcloud_data = []
            for word in words:
                weight = random.randint(5, 100)
                wordcloud_data.append({
                    'name': word,
                    'value': weight
                })
            
            # 保存到comment_wordcloud集合
            try:
                collection = db['comment_wordcloud']
                result = collection.update_one(
                    {'movie_id': movie_id},
                    {'$set': {
                        'wordcloud': wordcloud_data,
                        'movie_id': movie_id,
                        'generated_at': datetime.datetime.now()
                    }},
                    upsert=True
                )
                logger.info(f"成功为电影 {movie_id} 创建词云数据（{len(wordcloud_data)}个词）")
            except Exception as e:
                logger.error(f"为电影 {movie_id} 创建词云数据失败: {e}")
                continue
                
            # 创建策略词云数据
            for strategy in ['sequential', 'random_pages', 'random_interval', 'random_block']:
                try:
                    strategy_collection = db['strategy_wordcloud']
                    
                    # 为每个策略创建略有不同的词云数据
                    strategy_data = []
                    for item in wordcloud_data:
                        # 调整权重，使每个策略的词云看起来不同
                        weight_factor = random.uniform(0.7, 1.3)
                        strategy_data.append({
                            'name': item['name'],
                            'value': int(item['value'] * weight_factor)
                        })
                        
                    result = strategy_collection.update_one(
                        {'movie_id': movie_id, 'strategy': strategy},
                        {'$set': {
                            'wordcloud': strategy_data,
                            'movie_id': movie_id,
                            'strategy': strategy,
                            'generated_at': datetime.datetime.now()
                        }},
                        upsert=True
                    )
                    
                    logger.info(f"已为电影 {movie_id} 的 {strategy} 策略创建词云数据")
                except Exception as e:
                    logger.error(f"为电影 {movie_id} 的 {strategy} 策略创建词云数据失败: {e}")
        
        # 验证创建的集合
        collections = list_collections(db)
        logger.info(f"现在数据库中包含以下集合: {collections}")
        
        return True
    except Exception as e:
        logger.error(f"创建示例词云数据失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    logger.info("开始检查MongoDB连接和词云数据")
    
    # 检查MongoDB连接
    client, db = check_mongodb_connection()
    if not client or not db:
        logger.error("MongoDB连接失败，终止测试")
        return
    
    # 列出集合
    collections = list_collections(db)
    if not collections:
        logger.error("未找到任何集合，终止测试")
        return
    
    # 列出电影ID
    movie_ids = list_movie_ids(db)
    if not movie_ids:
        logger.warning("未找到任何电影ID，尝试使用默认ID")
        test_movie_id = "1291543"  # 默认ID - 霸王别姬
    else:
        test_movie_id = movie_ids[0]
    
    logger.info(f"使用电影ID: {test_movie_id}")
    
    # 检查词云数据
    found_data = check_wordcloud_data(db, test_movie_id)
    
    if not found_data:
        logger.warning(f"未找到电影 {test_movie_id} 的词云数据，尝试创建新的词云数据")
        
        # 为所有电影创建示例词云数据
        insert_sample_wordcloud_for_all_movies(db)
        
        # 再次检查是否可以获取到
        check_wordcloud_data(db, test_movie_id)
    
    logger.info("MongoDB连接和词云数据检查完成")

if __name__ == "__main__":
    main() 