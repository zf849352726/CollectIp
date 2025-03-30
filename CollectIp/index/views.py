from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from .models import IpData, Movie, ProxySettings, DoubanSettings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging
from ip_operator.services.crawler import start_crawl, start_douban_crawl
from ip_operator.services.scorer import start_score
import threading
from django.conf import settings
import os
from datetime import datetime, timedelta
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from index.mongodb_utils import MongoDBClient
from index.text_utils import TextProcessor
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

# Create your views here.
def login_view(request):
    if request.method == 'GET':
        return render(request, 'login.html')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # 设置session过期时间
            if remember:
                request.session.set_expiry(1209600)  # 两周
            else:
                request.session.set_expiry(0)  # 浏览器关闭即过期
                
            return redirect('ip_pool')  # 改为新的URL名称
        else:
            messages.error(request, '用户名或密码错误')
            return render(request, 'login.html')

def index(request):
    return render(request, 'index.html')

def register_view(request):
    if request.method == 'GET':
        return render(request, 'register.html')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # 表单验证
        if not username or not password1 or not password2:
            messages.error(request, '请填写所有字段')
            return render(request, 'register.html')
            
        if password1 != password2:
            messages.error(request, '两次输入的密码不一致')
            return render(request, 'register.html')
            
        if len(password1) < 8:
            messages.error(request, '密码长度至少为8个字符')
            return render(request, 'register.html')
            
        # 创建用户
        try:
            user = User.objects.create_user(username=username, password=password1)
            login(request, user)  # 注册成功后自动登录
            return redirect('index')
        except IntegrityError:
            messages.error(request, '用户名已存在')
            return render(request, 'register.html')

@login_required
def ip_pool_view(request):
    # 从数据库获取IP统计数据
    total_ips = IpData.objects.count()
    active_ips = IpData.objects.filter(score__gt=60).count()
    inactive_ips = total_ips - active_ips
    
    # 获取代理设置
    proxy_settings, _ = ProxySettings.objects.get_or_create(id=1, defaults={
        'crawler_interval': 3600,
        'score_interval': 1800,
        'min_score': 10
    })
    
    context = {
        'page_title': 'IP池管理',
        'active_menu': 'ip_pool_overview',
        'ip_stats': {
            'total': total_ips,
            'active': active_ips, 
            'inactive': inactive_ips
        },
        'proxy_settings': proxy_settings  # 确保设置数据传递到模板
    }
    return render(request, 'ip_pool.html', context)

@login_required
def ip_manage_view(request):
    # 获取所有IP数据
    ip_list = IpData.objects.all().order_by('-score')
    
    # 设置每页显示的数量
    per_page = 10
    paginator = Paginator(ip_list, per_page)
    
    # 获取当前页码
    page = request.GET.get('page', 1)
    
    try:
        # 获取当前页的数据
        ip_list = paginator.page(page)
    except:
        # 如果页码无效，显示第一页
        ip_list = paginator.page(1)
    
    context = {
        'active_menu': 'ip_manage',
        'page_title': 'IP管理',
        'ip_list': ip_list
    }
    return render(request, 'ip_pool.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def proxy_settings_view(request):
    """处理代理设置的API端点"""
    try:
        settings, created = ProxySettings.objects.get_or_create(
            id=1,
            defaults={
                'crawler_interval': 3600,
                'score_interval': 1800,
                'min_score': 10,
                'auto_crawler': False,
                'auto_score': False
            }
        )
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'data': {
                    'crawler_interval': settings.crawler_interval,
                    'score_interval': settings.score_interval,
                    'min_score': settings.min_score,
                    'auto_crawler': settings.auto_crawler,
                    'auto_score': settings.auto_score
                }
            })
        elif request.method == 'POST':
            try:
                crawler_interval = int(request.POST.get('crawler_interval', 0))
                score_interval = int(request.POST.get('score_interval', 0))
                min_score = int(request.POST.get('min_score', 0))                
                auto_crawler = request.POST.get('auto_crawler', 'off') == 'on'
                auto_score = request.POST.get('auto_score', 'off') == 'on'
                
                if crawler_interval < 60:
                    return JsonResponse({
                        'success': False,
                        'error': "爬虫间隔不能小于60秒"
                    })
                
                if score_interval < 60:
                    return JsonResponse({
                        'success': False,
                        'error': "评分间隔不能小于60秒"
                    })
                
                if not (0 <= min_score <= 100):
                    return JsonResponse({
                        'success': False,
                        'error': "最低分数必须在0-100之间"
                    })
                
                settings.crawler_interval = crawler_interval
                settings.score_interval = score_interval
                settings.min_score = min_score
                settings.auto_crawler = auto_crawler
                settings.auto_score = auto_score
                settings.save()
                
                # 更新调度器设置
                try:
                    from ip_operator.scheduler import update_intervals
                    update_intervals(
                        crawler_interval=crawler_interval,
                        score_interval=score_interval,
                        auto_crawler=auto_crawler,
                        auto_score=auto_score
                    )
                except Exception as e:
                    logger.error(f"更新调度器设置失败: {e}")
                
                return JsonResponse({
                    'success': True,
                    'message': '设置已更新'
                })
                
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': "请输入有效的数字"
                })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def monitoring_view(request):
    return render(request, 'ip_pool.html', {'active_menu': 'monitoring'})

@login_required
def operation_log_view(request):
    return render(request, 'ip_pool.html', {'active_menu': 'operation_log'})

@login_required
def wechat_view(request):
    # 示例数据
    articles = [
        {
            'title': '示例文章1',
            'description': '这是一篇示例文章的描述内容...',
            'cover_image': 'https://via.placeholder.com/300x200',
            'read_count': 1234,
            'like_count': 56,
            'publish_date': '2024-03-21'
        },
        {
            'title': '示例文章2',
            'description': '这是另一篇示例文章的描述内容...',
            'cover_image': 'https://via.placeholder.com/300x200',
            'read_count': 789,
            'like_count': 34,
            'publish_date': '2024-03-20'
        },
        # 可以添加更多示例文章
    ]
    
    context = {
        'active_menu': 'article_manage',
        'page_title': '文章管理',
        'articles': articles
    }
    return render(request, 'wechat.html', context)

@login_required
def wechat_overview(request):
    return render(request, 'wechat.html', {'active_menu': 'wechat_overview'})

@login_required
def article_manage(request):
    return render(request, 'wechat.html', {'active_menu': 'article_manage'})

@login_required
def media_library(request):
    return render(request, 'wechat.html', {'active_menu': 'media_library'})

@login_required
def data_analysis(request):
    return render(request, 'wechat.html', {'active_menu': 'data_analysis'})

@login_required
def wechat_settings(request):
    return render(request, 'wechat.html', {'active_menu': 'wechat_settings'})

@login_required
def douban(request):
    # 直接重定向到数据概览页面
    return redirect('douban_overview')

@login_required
def douban_overview(request):
    # 获取数据统计
    try:
        from datetime import datetime, timedelta
        
        total_movies = Movie.objects.count()
        
        # 计算周和月的时间范围
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
        month_start = datetime(now.year, now.month, 1)
        
        # 统计当周和当月新增的电影数量
        weekly_movies = Movie.objects.filter(created_at__gte=week_start).count()
        monthly_movies = Movie.objects.filter(created_at__gte=month_start).count()
        
        # 获取评分最高、最受欢迎和最新的电影
        top_rated_movies = Movie.objects.order_by('-rating')[:5]  # 评分最高的5部电影
        most_popular_movies = Movie.objects.order_by('-rating_count')[:5]  # 评分人数最多的5部电影
        latest_movies = Movie.objects.order_by('-updated_at')[:5]  # 最近更新的5部电影
        
        context = {
            'active_menu': 'douban_overview',
            'page_title': '豆瓣数据概览',
            'total_movies': total_movies,
            'weekly_movies': weekly_movies,
            'monthly_movies': monthly_movies,
            'top_rated_movies': top_rated_movies,
            'most_popular_movies': most_popular_movies,
            'latest_movies': latest_movies
        }
        
        return render(request, 'douban.html', context)
    except Exception as e:
        logger.error(f"获取豆瓣数据概览失败: {str(e)}")
        return render(request, 'douban.html', {
            'active_menu': 'douban_overview',
            'page_title': '豆瓣数据概览',
            'error': f"获取数据概览失败: {str(e)}"
        })

@login_required
def movie_list(request):
    # 从数据库获取所有电影数据
    try:
        movies = Movie.objects.all().order_by('-rating', '-rating_count')
        
        # 设置分页
        paginator = Paginator(movies, 10)  # 每页10条记录
        page = request.GET.get('page', 1)
        
        try:
            movies = paginator.page(page)
        except:
            movies = paginator.page(1)
        
        context = {
            'active_menu': 'movie_list',
            'page_title': '电影列表',
            'movies': movies
        }
        
        return render(request, 'douban.html', context)
    except Exception as e:
        logger.error(f"获取电影列表失败: {str(e)}")
        return render(request, 'douban.html', {
            'active_menu': 'movie_list',
            'page_title': '电影列表',
            'error': f"获取电影列表失败: {str(e)}"
        })

@login_required
def tv_list(request):
    return render(request, 'douban.html', {'active_menu': 'tv_list'})

@login_required
def data_trend(request):
    return render(request, 'douban.html', {'active_menu': 'data_trend'})

@login_required
@require_http_methods(["GET", "POST"])
def douban_settings(request):
    """处理豆瓣设置请求，支持GET和POST方法"""
    try:
        # 创建默认设置
        from django.db import models
        
        # 检查是否有DoubanSettings模型
        try:
            # 尝试从index.models导入DoubanSettings
            from .models import DoubanSettings
        except ImportError:
            # 如果不存在，创建一个临时类
            class DoubanSettings(models.Model):
                crawl_interval = models.IntegerField(default=60)  # 默认60分钟
                movie_count = models.IntegerField(default=10)     # 默认采集10部电影
                tv_count = models.IntegerField(default=5)         # 默认采集5部电视剧
                
                class Meta:
                    app_label = 'index'
        
        # 获取或创建设置记录
        settings_obj, created = DoubanSettings.objects.get_or_create(
            id=1,
            defaults={
                'crawl_interval': 60,
                'movie_count': 10,
                'tv_count': 5
            }
        )
        
        if request.method == 'GET':
            # 对于GET请求，返回当前设置
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # 如果是AJAX请求，返回JSON数据
                return JsonResponse({
                    'success': True,
                    'data': {
                        'crawl_interval': settings_obj.crawl_interval,
                        'movie_count': settings_obj.movie_count,
                        'tv_count': settings_obj.tv_count
                    }
                })
            else:
                # 如果是普通请求，返回HTML页面
                return render(request, 'douban.html', {
                    'active_menu': 'douban_settings',
                    'page_title': '豆瓣设置',
                    'settings': settings_obj
                })
                
        elif request.method == 'POST':
            # 对于POST请求，更新设置
            try:
                crawl_interval = int(request.POST.get('crawl_interval', 60))
                movie_count = int(request.POST.get('movie_count', 10))
                tv_count = int(request.POST.get('tv_count', 5))
                
                # 验证设置值
                if crawl_interval < 1:
                    return JsonResponse({
                        'success': False,
                        'error': "采集间隔不能小于1分钟"
                    })
                
                if movie_count < 1 or tv_count < 1:
                    return JsonResponse({
                        'success': False,
                        'error': "采集数量必须大于0"
                    })
                
                # 更新设置
                settings_obj.crawl_interval = crawl_interval
                settings_obj.movie_count = movie_count
                settings_obj.tv_count = tv_count
                settings_obj.save()
                
                return JsonResponse({
                    'success': True,
                    'message': '设置已更新'
                })
                
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': "请输入有效的数字"
                })
    except Exception as e:
        logger.error(f"处理豆瓣设置请求失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["POST"])
def crawl_movie_view(request):
    """接收电影名称并启动豆瓣爬虫"""
    import json
    from ip_operator.services.crawler import start_douban_crawl
    import os
    from datetime import datetime, timedelta
    
    # 创建锁文件目录
    lock_dir = os.path.join(settings.BASE_DIR, 'locks')
    os.makedirs(lock_dir, exist_ok=True)
    lock_file = os.path.join(lock_dir, 'douban_crawler.lock')
    
    try:
        # 从请求体获取电影名称
        data = json.loads(request.body)
        movie_name = data.get('movie_name')
        
        if not movie_name:
            return JsonResponse({
                'success': False,
                'error': '电影名称不能为空'
            })
            
        # 检查锁文件以防止频繁启动
        if os.path.exists(lock_file):
            # 检查锁文件的创建时间
            lock_time = datetime.fromtimestamp(os.path.getmtime(lock_file))
            time_diff = datetime.now() - lock_time
            
            # 如果锁文件创建时间在5分钟内，拒绝请求
            if time_diff < timedelta(minutes=5):
                logger.warning(f"拒绝重复启动爬虫请求: {movie_name}, 上一次启动于 {time_diff.seconds} 秒前")
                return JsonResponse({
                    'success': False,
                    'error': f'爬虫正在运行中，请等待5分钟后再试 ({5-int(time_diff.seconds/60)} 分钟后可再次启动)'
                })
                
            # 如果锁文件过期，删除它
            os.remove(lock_file)
        
        # 创建新的锁文件
        with open(lock_file, 'w') as f:
            f.write(f"Douban crawler started at {datetime.now()} for movie: {movie_name}")
            
        # 记录日志
        logger.info(f"接收到电影采集请求: {movie_name}")
        
        # 使用我们的新方法启动爬虫
        result = start_douban_crawl(movie_name)
        
        if result:
            return JsonResponse({
                'success': True,
                'message': f'已开始采集电影: {movie_name}'
            })
        else:
            # 如果启动失败，删除锁文件以允许重试
            if os.path.exists(lock_file):
                os.remove(lock_file)
                
            return JsonResponse({
                'success': False,
                'error': '爬虫启动失败，请查看日志'
            })
    except Exception as e:
        logger.error(f"启动电影采集失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 发生异常时也删除锁文件
        if os.path.exists(lock_file):
            os.remove(lock_file)
            
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@require_http_methods(["POST"])
def crawl_once_view(request):
    """执行一次IP采集"""
    try:
        # 在新线程中启动爬虫
        thread = threading.Thread(target=start_crawl)
        thread.start()
        
        return JsonResponse({
            'success': True,
            'message': '已开始执行IP采集'
        })
    except Exception as e:
        logger.error(f"启动爬虫失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@require_http_methods(["POST"])
def score_once_view(request):
    """执行一次IP评分"""
    try:
        # 在新线程中启动评分
        thread = threading.Thread(target=start_score)
        thread.start()
        
        return JsonResponse({
            'success': True,
            'message': '已开始执行IP评分'
        })
    except Exception as e:
        logger.error(f"启动评分失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def movie_detail(request, movie_id):
    """电影详情页面视图"""
    try:
        # 获取电影详情
        movie = Movie.objects.get(id=movie_id)
        
        # 准备上下文数据
        context = {
            'movie': movie,
            'comment_keywords': [],
            'rating_trends': [],
            'sequential_wordcloud': [],
            'random_pages_wordcloud': [],
            'random_interval_wordcloud': [],
            'random_block_wordcloud': []
        }
        
        # 尝试获取MongoDB数据
        try:
            # 导入MongoDB客户端
            from index.mongodb_utils import MongoDBClient
            import json
            
            # 获取MongoDB客户端实例
            mongo_client = MongoDBClient.get_instance()
            
            # 获取电影评论关键词（用于词云展示）
            comment_keywords = mongo_client.get_comment_keywords(movie_id)
            
            # 如果没有评论关键词数据，尝试生成词云数据
            if not comment_keywords:
                comment_keywords = mongo_client.get_wordcloud_data(movie_id)
                
            # 根据采集策略获取相应的词云数据
            sequential_wordcloud = mongo_client.get_wordcloud_data_by_strategy(movie_id, 'sequential')
            random_pages_wordcloud = mongo_client.get_wordcloud_data_by_strategy(movie_id, 'random_pages')
            random_interval_wordcloud = mongo_client.get_wordcloud_data_by_strategy(movie_id, 'random_interval')
            random_block_wordcloud = mongo_client.get_wordcloud_data_by_strategy(movie_id, 'random_block')
            
            # 获取评分趋势数据
            rating_trends = []
            try:
                # 从MongoDB获取评论趋势数据
                trends_data = mongo_client.get_comment_trends(movie_id, days=60)
                
                # 处理趋势数据
                if trends_data:
                    for item in trends_data:
                        trend_item = {
                            'date': item.get('_id', ''),
                            'rating': round(float(item.get('avg_rating', 0)), 1),
                            'count': item.get('count', 0)
                        }
                        rating_trends.append(trend_item)
                
                # 记录获取到的趋势数据
                logger.info(f"获取到电影 {movie_id} 的评分趋势数据: {len(rating_trends)} 条")
                
            except Exception as e:
                logger.error(f"获取评分趋势数据失败: {str(e)}")
            
            # 添加到上下文
            context['comment_keywords'] = comment_keywords
            context['sequential_wordcloud'] = sequential_wordcloud
            context['random_pages_wordcloud'] = random_pages_wordcloud
            context['random_interval_wordcloud'] = random_interval_wordcloud
            context['random_block_wordcloud'] = random_block_wordcloud
            context['rating_trends'] = rating_trends
            
            # 记录获取到的数据
            logger.info(f"获取到电影 {movie_id} 的词云数据: {len(comment_keywords)} 个关键词")
            
        except Exception as e:
            logger.error(f"获取MongoDB数据失败: {str(e)}")
        
        # 返回详情页面，包含电影信息和词云数据
        return render(request, 'douban_detail.html', context)
        
    except Movie.DoesNotExist:
        return render(request, 'error.html', {'error_message': '电影不存在'})
    except Exception as e:
        logger.error(f"电影详情页加载失败: {str(e)}")
        return render(request, 'error.html', {'error_message': '加载详情页失败'})

def process_comment_analysis_async(movie_id):
    """异步处理评论分析任务"""
    try:
        mongo_client = MongoDBClient.get_instance()
        
        # 生成词云数据
        wordcloud_data = mongo_client.get_wordcloud_data(movie_id)
        cache.set(f'movie_{movie_id}_wordcloud', wordcloud_data, timeout=3600*24)  # 缓存24小时
        
        # 情感统计
        sentiment_stats = mongo_client.get_sentiment_stats(movie_id)
        cache.set(f'movie_{movie_id}_sentiment', sentiment_stats, timeout=3600*24)
        
        # 评分统计
        rating_stats = mongo_client.get_rating_stats(movie_id)
        cache.set(f'movie_{movie_id}_ratings', rating_stats, timeout=3600*24)
        
        # 关键词统计
        keywords = mongo_client.get_comment_keywords(movie_id)
        cache.set(f'movie_{movie_id}_keywords', keywords, timeout=3600*24)
        
        # 随机采样评论（用于展示）
        sample_comments = mongo_client.sample_comments(movie_id, sample_size=100)
        cache.set(f'movie_{movie_id}_sample_comments', sample_comments, timeout=3600*12)
        
        # 评论趋势
        trends = mongo_client.get_comment_trends(movie_id, days=30)
        cache.set(f'movie_{movie_id}_trends', trends, timeout=3600*24)
        
        logger.info(f"电影ID {movie_id} 的评论分析任务已完成")
    except Exception as e:
        logger.error(f"异步处理评论分析失败: {str(e)}")

@cache_page(60 * 15)  # 缓存15分钟
def movie_comment_analysis(request, movie_id):
    """电影评论分析页面"""
    try:
        # 尝试从缓存获取数据
        wordcloud_data = cache.get(f'movie_{movie_id}_wordcloud')
        sentiment_stats = cache.get(f'movie_{movie_id}_sentiment')
        rating_stats = cache.get(f'movie_{movie_id}_ratings')
        keywords = cache.get(f'movie_{movie_id}_keywords')
        trends = cache.get(f'movie_{movie_id}_trends')
        
        # 如果缓存中没有数据，则实时获取并触发异步更新
        mongo_client = MongoDBClient.get_instance()
        
        if wordcloud_data is None:
            wordcloud_data = mongo_client.get_wordcloud_data(movie_id)
            # 触发异步更新
            threading.Thread(
                target=process_comment_analysis_async,
                args=(movie_id,)
            ).start()
        
        if sentiment_stats is None:
            sentiment_stats = mongo_client.get_sentiment_stats(movie_id)
        
        if rating_stats is None:
            rating_stats = mongo_client.get_rating_stats(movie_id)
            
        if keywords is None:
            keywords = mongo_client.get_comment_keywords(movie_id)
            
        if trends is None:
            trends = mongo_client.get_comment_trends(movie_id, days=30)
        
        # 从MySQL获取电影基本信息
        movie = Movie.objects.filter(id=movie_id).first()
        
        # 构建上下文
        context = {
            'movie': movie,
            'wordcloud_data': json.dumps(wordcloud_data),
            'sentiment_stats': sentiment_stats,
            'rating_stats': rating_stats,
            'keywords': keywords,
            'trends': json.dumps(trends),
        }
        
        return render(request, 'movie_comment_analysis.html', context)
        
    except Exception as e:
        logger.error(f"电影评论分析页面加载失败: {str(e)}")
        return render(request, 'error.html', {'error_message': '评论分析加载失败，请稍后重试'})

def trigger_comment_processing(request):
    """触发评论处理任务（可从管理界面调用）"""
    if request.method == 'POST':
        movie_id = request.POST.get('movie_id')
        if movie_id:
            # 启动异步处理
            threading.Thread(
                target=process_comment_analysis_async,
                args=(int(movie_id),)
            ).start()
            return JsonResponse({'status': 'success', 'message': '评论处理任务已启动'})
        return JsonResponse({'status': 'error', 'message': '未提供电影ID'})
    return JsonResponse({'status': 'error', 'message': '请求方法错误'})

@require_POST
@csrf_exempt
def crawl_movie(request):
    try:
        # 解析JSON请求
        data = json.loads(request.body)
        movie_name = data.get('movie_name')
        comment_strategy = data.get('comment_strategy', 'sequential')
        strategy_params = data.get('strategy_params', {})
        
        if not movie_name:
            return JsonResponse({'status': 'error', 'message': '电影名称不能为空'})
        
        # 构造爬虫参数
        spider_params = {
            'movie_names': movie_name,
            'comment_strategy': comment_strategy
        }
        
        # 添加策略特定参数
        for key, value in strategy_params.items():
            spider_params[key] = value
        
        # 启动爬虫任务（保持原有逻辑）
        # ...
        
        return JsonResponse({'status': 'success', 'movie_id': movie_id})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})



