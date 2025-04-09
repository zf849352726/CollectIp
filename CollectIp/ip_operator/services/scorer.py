import logging
from django.db import transaction
from index.models import IpData
from ..ip_scorer import IPScorer
from django.conf import settings

# 设置日志
logger = logging.getLogger('ip_operator')


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
            
            min_score = getattr(settings, 'IP_POOL_CONFIG', {}).get('MIN_SCORE', 60)
            
            # 批量更新分数
            updated_count = 0
            deleted_count = 0
            low_score_servers = []
            
            for server, score in scores.items():
                IpData.objects.filter(server=server).update(score=score)
                updated_count += 1
                
                # 记录低分IP
                if score < min_score:
                    low_score_servers.append(server)
            
            # 删除低分IP
            if low_score_servers:
                deleted_count = IpData.objects.filter(server__in=low_score_servers).delete()[0]
                logger.warning(f"已删除 {deleted_count} 个低分IP")
            
            # 只记录总体结果，不记录每个IP的分数
            logger.warning(f"IP评分完成: 共更新 {updated_count} 个IP")
            
            return True
    except Exception as e:
        logger.error(f"评分失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False 