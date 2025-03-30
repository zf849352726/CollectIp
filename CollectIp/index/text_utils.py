import re
import jieba
import jieba.analyse
from collections import Counter
import logging
from snownlp import SnowNLP
import numpy as np
from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)

class TextProcessor:
    """文本处理工具类，用于评论文本的预处理和分析"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清洗文本，去除无效字符"""
        try:
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
        except Exception as e:
            logger.error(f"文本清洗失败: {str(e)}")
            return text
    
    @staticmethod
    def analyze_sentiment(text: str) -> Tuple[int, float]:
        """分析文本情感"""
        try:
            if not text.strip():
                return 0, 0.5
                
            # 使用SnowNLP进行情感分析
            s = SnowNLP(text)
            score = s.sentiments
            
            # 根据得分判断情感倾向
            if score > 0.6:
                sentiment = 1  # 正面
            elif score < 0.4:
                sentiment = -1  # 负面
            else:
                sentiment = 0  # 中性
                
            return sentiment, round(score, 4)
        except Exception as e:
            logger.error(f"情感分析失败: {str(e)}")
            return 0, 0.5
    
    @staticmethod
    def extract_keywords(text: str, top_n: int = 5) -> List[str]:
        """提取文本关键词"""
        try:
            if not text.strip():
                return []
                
            # 使用jieba提取关键词
            keywords = jieba.analyse.extract_tags(text, topK=top_n)
            return keywords
        except Exception as e:
            logger.error(f"关键词提取失败: {str(e)}")
            return []
    
    @staticmethod
    def generate_wordcloud_data(texts: List[str], top_n: int = 100) -> List[Dict]:
        """生成词云数据"""
        try:
            if not texts:
                return []
                
            # 合并所有文本
            combined_text = ' '.join(texts)
            
            # 提取关键词及其权重
            keywords = jieba.analyse.extract_tags(combined_text, topK=top_n, withWeight=True)
            
            # 转换为词云数据格式
            wordcloud_data = [
                {"name": word, "value": round(weight * 100, 2)}
                for word, weight in keywords
            ]
            
            return wordcloud_data
        except Exception as e:
            logger.error(f"生成词云数据失败: {str(e)}")
            return []
    
    @staticmethod
    def generate_summary(text: str, max_length: int = 200) -> str:
        """生成文本摘要"""
        try:
            if not text.strip():
                return ""
                
            # 使用jieba提取关键句子
            sentences = re.split(r'[。！？]', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return ""
                
            # 计算每个句子的重要性得分
            sentence_scores = []
            for sentence in sentences:
                # 使用关键词权重作为句子重要性得分
                keywords = jieba.analyse.extract_tags(sentence, topK=5, withWeight=True)
                score = sum(weight for _, weight in keywords)
                sentence_scores.append((sentence, score))
                
            # 按得分排序
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 选择得分最高的句子，直到达到最大长度
            summary = ""
            current_length = 0
            
            for sentence, _ in sentence_scores:
                if current_length + len(sentence) > max_length:
                    break
                summary += sentence + "。"
                current_length += len(sentence)
                
            return summary
        except Exception as e:
            logger.error(f"生成文本摘要失败: {str(e)}")
            return "" 