from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import DoubanMovie, DoubanComment
from django.db import connection
import logging

logger = logging.getLogger(__name__)

@login_required
def delete_movie(request, movie_id):
    """删除电影"""
    if request.method == 'POST':
        try:
            # 获取电影对象
            movie = DoubanMovie.objects.get(id=movie_id)
            
            # 删除电影相关的评论
            DoubanComment.objects.filter(movie_id=movie_id).delete()
            
            # 删除电影
            movie.delete()
            
            # 获取所有剩余电影并按ID排序
            remaining_movies = DoubanMovie.objects.all().order_by('id')
            
            # 重新编号所有电影
            for index, movie in enumerate(remaining_movies, 1):
                # 如果当前ID不等于新的序号，则更新
                if movie.id != index:
                    # 先保存旧的ID
                    old_id = movie.id
                    # 更新ID
                    movie.id = index
                    # 保存更新
                    movie.save(force_update=True)
                    logger.info(f"电影ID从 {old_id} 更新为 {index}")
            
            # 重置数据库自增ID
            try:
                with connection.cursor() as cursor:
                    # 获取当前表名
                    table_name = DoubanMovie._meta.db_table
                    # 获取当前最大ID
                    cursor.execute(f"SELECT MAX(id) FROM {table_name}")
                    max_id = cursor.fetchone()[0] or 0
                    # 设置自增ID为当前最大ID+1
                    cursor.execute(f"ALTER TABLE {table_name} AUTO_INCREMENT = {max_id + 1}")
                    logger.info(f"已重置{table_name}表的自增ID为 {max_id + 1}")
            except Exception as e:
                logger.error(f"重置自增ID失败: {str(e)}")
            
            return JsonResponse({'success': True, 'message': '电影删除成功'})
        except DoubanMovie.DoesNotExist:
            return JsonResponse({'success': False, 'error': '电影不存在'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'})

@login_required
def toggle_movie_published(request, movie_id):
    """切换电影的发表状态"""
    if request.method == 'POST':
        try:
            # 获取电影对象
            movie = DoubanMovie.objects.get(id=movie_id)
            
            # 切换发表状态
            movie.is_published = not movie.is_published
            movie.save()
            
            # 返回成功响应
            return JsonResponse({
                'success': True,
                'is_published': movie.is_published,
                'message': f'电影 "{movie.title}" {"已发表" if movie.is_published else "已取消发表"}'
            })
        except DoubanMovie.DoesNotExist:
            return JsonResponse({'success': False, 'error': '电影不存在'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'}) 