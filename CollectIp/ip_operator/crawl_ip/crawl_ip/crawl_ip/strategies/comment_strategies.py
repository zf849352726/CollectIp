# 评论采集策略实现文件
import random
import logging
import abc
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CommentStrategy(abc.ABC):
    """评论采集策略的抽象基类"""
    
    @abc.abstractmethod
    def get_pages_to_crawl(self, total_pages: int) -> List[int]:
        """
        确定要采集的页码列表
        
        Args:
            total_pages: 评论的总页数
            
        Returns:
            要采集的页码列表
        """
        pass
    
    @abc.abstractmethod
    def get_name(self) -> str:
        """获取策略名称"""
        pass


class SequentialStrategy(CommentStrategy):
    """顺序采集策略 - 从第一页开始连续采集一定数量的页面"""
    
    def __init__(self, max_pages: int = 5):
        self.max_pages = max_pages
    
    def get_pages_to_crawl(self, total_pages: int) -> List[int]:
        """返回前N页的页码列表"""
        pages = min(total_pages, self.max_pages)
        return list(range(1, pages + 1))
    
    def get_name(self) -> str:
        return f"顺序采集(最多{self.max_pages}页)"


class RandomPagesStrategy(CommentStrategy):
    """随机页码策略 - 在总页数范围内随机选择若干页进行采集"""
    
    def __init__(self, sample_size: int = 5):
        self.sample_size = sample_size
    
    def get_pages_to_crawl(self, total_pages: int) -> List[int]:
        """返回随机选择的页码列表"""
        pages_to_sample = min(total_pages, self.sample_size)
        if total_pages <= 1:
            return [1]
        
        # 随机选择页码
        pages = random.sample(range(1, total_pages + 1), pages_to_sample)
        # 按页码顺序排序，减少页面跳转
        return sorted(pages)
    
    def get_name(self) -> str:
        return f"随机页码采集(采集{self.sample_size}页)"


class RandomIntervalStrategy(CommentStrategy):
    """随机间隔策略 - 使用随机间隔跳页采集"""
    
    def __init__(self, max_interval: int = 3, max_pages: int = 5):
        self.max_interval = max_interval
        self.max_pages = max_pages
    
    def get_pages_to_crawl(self, total_pages: int) -> List[int]:
        """返回以随机间隔方式选择的页码列表"""
        if total_pages <= 1:
            return [1]
            
        pages = []
        current_page = 1
        pages.append(current_page)
        
        while len(pages) < self.max_pages and current_page < total_pages:
            # 随机确定间隔
            interval = random.randint(1, self.max_interval)
            current_page += interval
            
            if current_page <= total_pages:
                pages.append(current_page)
        
        return pages
    
    def get_name(self) -> str:
        return f"随机间隔采集(最大间隔{self.max_interval}页)"


class RandomBlockStrategy(CommentStrategy):
    """随机区块策略 - 随机选择起始页，然后连续采集一个区块"""
    
    def __init__(self, block_size: int = 3):
        self.block_size = block_size
    
    def get_pages_to_crawl(self, total_pages: int) -> List[int]:
        """返回随机区块的页码列表"""
        if total_pages <= 1:
            return [1]
            
        # 确保区块不会超出总页数
        if self.block_size >= total_pages:
            return list(range(1, total_pages + 1))
            
        # 随机选择起始页码
        max_start_page = total_pages - self.block_size + 1
        start_page = random.randint(1, max_start_page)
        
        # 返回连续区块页码
        return list(range(start_page, start_page + self.block_size))
    
    def get_name(self) -> str:
        return f"随机区块采集(区块大小{self.block_size}页)"


# 策略工厂，用于获取指定的策略实例
class CommentStrategyFactory:
    """评论采集策略工厂"""
    
    @staticmethod
    def get_strategy(strategy_type: str, **kwargs) -> CommentStrategy:
        """
        获取指定类型的策略实例
        
        Args:
            strategy_type: 策略类型名称
            **kwargs: 传递给策略构造函数的参数
            
        Returns:
            策略实例
        """
        strategies = {
            'sequential': SequentialStrategy,
            'random_pages': RandomPagesStrategy,
            'random_interval': RandomIntervalStrategy,
            'random_block': RandomBlockStrategy
        }
        
        if strategy_type not in strategies:
            logger.warning(f"未知的策略类型: {strategy_type}，使用默认的顺序策略")
            return SequentialStrategy(**kwargs)
            
        return strategies[strategy_type](**kwargs)


# 使用示例
def get_random_strategy() -> CommentStrategy:
    """随机选择一个采集策略"""
    strategies = [
        RandomPagesStrategy(sample_size=random.randint(3, 8)),
        RandomIntervalStrategy(max_interval=random.randint(2, 5), max_pages=random.randint(3, 8)),
        RandomBlockStrategy(block_size=random.randint(2, 5)),
        SequentialStrategy(max_pages=random.randint(3, 8))
    ]
    return random.choice(strategies) 