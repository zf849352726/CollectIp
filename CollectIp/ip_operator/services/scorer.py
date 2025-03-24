import logging
from django.db import transaction
from index.models import IpData
from ..ip_scorer import IPScorer
from django.conf import settings

logger = logging.getLogger(__name__)

def start_score():
    """评分服务"""
    try:
        with transaction.atomic():
            # 获取所有IP
            ips = IpData.objects.all()
            ip_list = [ip.server for ip in ips]
            
            if not ip_list:
                logger.warning("IP池为空")
                return True
            
            # 评分
            scorer = IPScorer()
            scores = scorer.score_ip_pool(ip_list)
            
            min_score = settings.IP_POOL_CONFIG['MIN_SCORE']
            
            # 批量更新分数
            for server, score in scores.items():
                IpData.objects.filter(server=server).update(score=score)
                logger.info(f"IP {server} 更新分数: {score}")
            
            # 删除低分IP
            IpData.objects.filter(score__lt=min_score).delete()
            
            return True
    except Exception as e:
        logger.error(f"评分失败: {e}")
        return False 