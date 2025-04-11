from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import DoubanMovie, DoubanComment

@login_required
def delete_movie(request):
    """删除电影"""
    if request.method == 'POST':
        try:
            movie_id = request.POST.get('movie_id')
            if not movie_id:
                return JsonResponse({'success': False, 'error': '电影ID不能为空'})
            
            # 获取电影对象
            movie = DoubanMovie.objects.get(id=movie_id)
            
            # 删除电影相关的评论
            DoubanComment.objects.filter(movie_id=movie_id).delete()
            
            # 删除电影
            movie.delete()
            
            # 重新编号所有电影
            movies = DoubanMovie.objects.all().order_by('id')
            for index, movie in enumerate(movies, 1):
                movie.id = index
                movie.save()
            
            return JsonResponse({'success': True})
        except DoubanMovie.DoesNotExist:
            return JsonResponse({'success': False, 'error': '电影不存在'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '无效的请求方法'}) 