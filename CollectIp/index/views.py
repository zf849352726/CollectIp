from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from .models import IpData, Movie, ProxySettings, DoubanSettings, Collection
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging
from ip_operator.services.scorer import start_score
from ip_operator.services.celery_crawler import start_crawl_ip, start_crawl_douban, check_task_status
import threading
from django.conf import settings
import os
from datetime import datetime, timedelta
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from index.mongodb_utils import MongoDBClient
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.http import HttpResponse
from django.middleware.csrf import get_token
import re
import time

logger = logging.getLogger(__name__)

# Create your views here.
def login_view(request):
    if request.method == 'GET':
        # 确保创建新的CSRF令牌
        request.META["CSRF_COOKIE_USED"] = True
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
                
            # 确保CSRF令牌在登录后更新
            request.META["CSRF_COOKIE_USED"] = True
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
                'auto_score': False,
                'captcha_retries': 5
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
                    'auto_score': settings.auto_score,
                    'captcha_retries': settings.captcha_retries
                }
            })
        elif request.method == 'POST':
            try:
                crawler_interval = int(request.POST.get('crawler_interval', 0))
                score_interval = int(request.POST.get('score_interval', 0))
                min_score = int(request.POST.get('min_score', 0))                
                auto_crawler = request.POST.get('auto_crawler', 'off') == 'on'
                auto_score = request.POST.get('auto_score', 'off') == 'on'
                captcha_retries = int(request.POST.get('captcha_retries', 5))
                
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
                    
                if not (1 <= captcha_retries <= 20):
                    return JsonResponse({
                        'success': False,
                        'error': "验证码最大重试次数必须在1-20之间"
                    })
                
                settings.crawler_interval = crawler_interval
                settings.score_interval = score_interval
                settings.min_score = min_score
                settings.auto_crawler = auto_crawler
                settings.auto_score = auto_score
                settings.captcha_retries = captcha_retries
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
    # 获取合集数据统计
    total_collections = Collection.objects.count()
    latest_collections = Collection.objects.filter(is_published=True).order_by('-updated_at')[:5].count()
    movie_collections = Collection.objects.filter(collection_type='movie').count()
    tv_collections = Collection.objects.filter(collection_type='tv').count()
    
    # 获取分页合集列表
    collections = Collection.objects.all().order_by('-updated_at')
    paginator = Paginator(collections, 6)  # 每页显示6个合集
    
    page = request.GET.get('page', 1)
    try:
        collections = paginator.page(page)
    except:
        collections = paginator.page(1)
    
    context = {
        'active_menu': 'wechat_overview',
        'page_title': '合集概览',
        'collection_stats': {
            'total': total_collections,
            'latest': latest_collections,
            'movie': movie_collections,
            'tv': tv_collections
        },
        'collection_list': collections
    }
    return render(request, 'wechat.html', context)

def article_manage(request):
    """电影合集管理视图"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # 获取类型筛选参数
    collection_type = request.GET.get('type', 'all')
    search_query = request.GET.get('q', '')
    page = request.GET.get('page', 1)
    
    # 查询合集列表
    collections = Collection.objects.all().order_by('-updated_at')
    
    # 应用筛选条件
    if collection_type and collection_type != 'all':
        collections = collections.filter(collection_type=collection_type)
        
    if search_query:
        collections = collections.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # 分页
    paginator = Paginator(collections, 12)  # 每页显示12个合集
    try:
        collection_list = paginator.page(page)
    except PageNotAnInteger:
        collection_list = paginator.page(1)
    except EmptyPage:
        collection_list = paginator.page(paginator.num_pages)
    
    # 统计信息
    collection_stats = {
        'total': Collection.objects.count(),
        'movie': Collection.objects.filter(collection_type='movie').count(),
        'tv': Collection.objects.filter(collection_type='tv').count(),
        'article': Collection.objects.filter(collection_type='article').count(),
        'published': Collection.objects.filter(is_published=True).count(),
    }
    
    context = {
        'active_menu': 'article_manage',
        'page_title': '合集管理',
        'collection_list': collection_list,
        'collection_stats': collection_stats,
        'current_type': collection_type,
        'search_query': search_query,
    }
    
    return render(request, 'wechat.html', context)

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
def crawl_movie(request):
    """启动豆瓣电影评论爬虫"""
    try:
        # 获取电影名称和策略参数
        movie_name = request.POST.get('movie_name', '').strip()
        comment_strategy = request.POST.get('strategy', 'sequential').strip()
        
        if not movie_name:
            return JsonResponse({
                'success': False,
                'error': '电影名称不能为空',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # 检查是否存在锁文件（旧版本兼容，可以移除）
        lock_file = os.path.join(settings.BASE_DIR, 'logs', f'crawler_{movie_name}.lock')
        if os.path.exists(lock_file):
            # 检查锁文件是否过期（超过1小时）
            if os.path.getmtime(lock_file) < (time.time() - 3600):
                os.remove(lock_file)
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'该电影的爬虫任务正在进行中，请稍后再试: {movie_name}',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # 获取其他参数
        try:
            max_pages = int(request.POST.get('max_pages', 5))
            sample_size = int(request.POST.get('sample_size', 5))
            max_interval = int(request.POST.get('max_interval', 3))
            block_size = int(request.POST.get('block_size', 3))
            use_random_strategy = request.POST.get('use_random', 'false').lower() == 'true'
        except ValueError as e:
            logger.warning(f"参数转换错误，使用默认值: {str(e)}")
            # 使用默认值
            if comment_strategy == 'sequential':
                max_pages = 5
            elif comment_strategy == 'random_pages':
                sample_size = 5
            elif comment_strategy == 'random_interval':
                max_interval = 3
                max_pages = 5
            elif comment_strategy == 'random_block':
                block_size = 3
        
        # 启动Celery任务来爬取电影评论
        task = start_crawl_douban(
            movie_name=movie_name,
            strategy=comment_strategy,
            max_pages=max_pages,
            sample_size=sample_size,
            max_interval=max_interval,
            block_size=block_size,
            use_random_strategy=use_random_strategy
        )
        
        # 检查任务是否成功启动
        if not task:
            return JsonResponse({
                'success': False,
                'error': f'无法启动爬虫任务，可能该电影的爬虫已在运行中: {movie_name}',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
        # 记录任务启动信息
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"豆瓣电影爬虫任务已提交 - 时间: {timestamp}, 电影: {movie_name}, 策略: {comment_strategy}, 任务ID: {task.id}")
        
        return JsonResponse({
            'success': True,
            'message': f'已开始采集电影: {movie_name}, 使用策略: {comment_strategy}',
            'timestamp': timestamp,
            'task_id': task.id,
            'details': f'采集操作启动于 {timestamp}，电影: {movie_name}，策略: {comment_strategy}。系统将自动爬取电影评论，完成后可在电影详情页查看。'
        })
    except Exception as e:
        logger.error(f"启动电影采集失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 发生异常时也删除锁文件（旧版本兼容）
        if 'lock_file' in locals() and os.path.exists(lock_file):
            os.remove(lock_file)
            
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'details': f'启动电影爬虫时发生错误: {str(e)}。请检查系统日志获取更多信息。'
        })

@login_required
@require_http_methods(["POST"])
def crawl_once_view(request):
    """执行一次IP采集"""
    try:
        # 记录启动时间
        start_time = timezone.now()
        timestamp = start_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取爬取类型
        crawl_type = request.POST.get('crawl_type', 'all')
        
        # 启动Celery任务执行IP采集
        task = start_crawl_ip(crawl_type=crawl_type)
        
        # 检查任务是否成功启动
        if not task:
            return JsonResponse({
                'success': False,
                'error': '无法启动IP爬取任务，可能已有相同类型的爬取任务正在运行',
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # 获取当前IP总数，用于后续对比
        current_ip_count = IpData.objects.count()
        
        # 记录执行信息到日志
        logger.info(f"IP采集任务已提交 - 时间: {timestamp}, 当前IP数: {current_ip_count}, 任务ID: {task.id}")
        
        return JsonResponse({
            'success': True,
            'message': '已开始执行IP采集',
            'timestamp': timestamp,
            'task_id': task.id,
            'details': f'采集操作启动于 {timestamp}，当前IP池中有 {current_ip_count} 个IP。系统将自动爬取新的IP，完成后会显示在IP列表中。'
        })
    except Exception as e:
        logger.error(f"启动IP爬虫任务失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'details': f'启动爬虫时发生错误: {str(e)}。请检查系统日志获取更多信息。'
        })

@login_required
@require_http_methods(["POST"])
def score_once_view(request):
    """执行一次IP评分"""
    try:
        # 记录启动时间
        start_time = timezone.now()
        timestamp = start_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取评分前的IP统计
        total_ips = IpData.objects.count()
        active_ips = IpData.objects.filter(score__gt=60).count()
        
        # 在新线程中启动评分
        thread = threading.Thread(target=start_score)
        thread.start()
        
        # 记录执行信息到日志
        logger.info(f"IP评分任务已启动 - 时间: {timestamp}, 当前IP数: {total_ips}, 活跃IP数: {active_ips}")
        
        return JsonResponse({
            'success': True,
            'message': '已开始执行IP评分',
            'timestamp': timestamp,
            'details': f'评分操作启动于 {timestamp}，当前IP池中有 {total_ips} 个IP，其中 {active_ips} 个活跃IP(分数>60)。系统将评估所有IP的质量并更新评分。'
        })
    except Exception as e:
        logger.error(f"启动评分失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'details': f'启动评分时发生错误: {str(e)}。请检查系统日志获取更多信息。'
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
            'comment_keywords': '[]',  # 默认为空JSON数组字符串
            'rating_trends': '[]',     # 默认为空JSON数组字符串
            'sequential_wordcloud': '[]',
            'random_pages_wordcloud': '[]',
            'random_interval_wordcloud': '[]',
            'random_block_wordcloud': '[]'
        }
        
        # 尝试获取MongoDB数据
        try:
            logger.info(f"开始获取电影 {movie_id} 的MongoDB数据")
            
            # 导入MongoDB客户端
            mongo_client = MongoDBClient.get_instance()
            if not mongo_client:
                logger.error("无法获取MongoDB客户端实例")
                raise Exception("MongoDB连接失败")
                
            logger.info("MongoDB客户端连接成功")
            
            # 获取电影评论关键词（用于词云展示）
            logger.info(f"尝试获取电影 {movie_id} 的评论关键词")
            
            # 调试MongoDB集合中评论的结构
            try:
                sample_comments = list(mongo_client.comments_collection.find({"movie_id": int(movie_id)}).limit(3))
                if sample_comments:
                    logger.info(f"电影 {movie_id} 评论样本: {sample_comments}")
                    logger.info(f"评论中关键词: {[c.get('keywords', []) for c in sample_comments]}")
                else:
                    logger.warning(f"电影 {movie_id} 没有评论数据")
            except Exception as e:
                logger.error(f"获取评论样本失败: {str(e)}")
            
            comment_keywords = mongo_client.get_comment_keywords(movie_id)
            
            if comment_keywords:
                logger.info(f"从MongoDB获取到评论关键词数据: {len(comment_keywords)} 个")
                # 记录数据样本帮助调试
                if len(comment_keywords) > 0:
                    logger.info(f"关键词数据样本: {comment_keywords[0]}")
            else:
                logger.warning(f"没有找到电影 {movie_id} 的评论关键词数据")
            
            # 如果没有评论关键词数据，尝试生成词云数据
            if not comment_keywords:
                logger.info(f"尝试获取电影 {movie_id} 的词云数据")
                wordcloud_data = mongo_client.get_wordcloud_data(movie_id)
                if wordcloud_data:
                    comment_keywords = wordcloud_data
                    logger.info(f"成功获取词云数据，共 {len(wordcloud_data)} 个关键词")
                    # 记录数据样本帮助调试
                    if len(wordcloud_data) > 0:
                        logger.info(f"词云数据样本: {wordcloud_data[0]}")
                else:
                    logger.warning(f"没有找到电影 {movie_id} 的词云数据，将使用示例数据")
                    # 添加生成示例词云数据的逻辑
                    comment_keywords = mongo_client.generate_strategy_wordcloud(movie_id, movie.title)
                    logger.info(f"已生成示例词云数据，共 {len(comment_keywords)} 个关键词")
            
            # 根据采集策略获取相应的词云数据
            logger.info(f"尝试获取电影 {movie_id} 的各种策略词云数据")
            sequential_wordcloud = mongo_client.get_wordcloud_data_by_strategy(movie_id, 'sequential') or []
            random_pages_wordcloud = mongo_client.get_wordcloud_data_by_strategy(movie_id, 'random_pages') or []
            random_interval_wordcloud = mongo_client.get_wordcloud_data_by_strategy(movie_id, 'random_interval') or []
            random_block_wordcloud = mongo_client.get_wordcloud_data_by_strategy(movie_id, 'random_block') or []
            
            logger.info(f"策略词云数据获取结果: 顺序={len(sequential_wordcloud)}项, 随机页码={len(random_pages_wordcloud)}项, " +
                       f"随机间隔={len(random_interval_wordcloud)}项, 随机区块={len(random_block_wordcloud)}项")
            
            # 获取评分趋势数据
            rating_trends = []
            try:
                # 从MongoDB获取评论趋势数据
                logger.info(f"尝试获取电影 {movie_id} 的评分趋势数据")
                trends_data = mongo_client.get_comment_trends(movie_id, days=60)
                
                # 处理趋势数据
                if trends_data:
                    for item in trends_data:
                        try:
                            trend_item = {
                                'date': item.get('_id', ''),
                                'rating': round(float(item.get('avg_rating', 0)), 1),
                                'count': item.get('count', 0)
                            }
                            rating_trends.append(trend_item)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"处理趋势数据时出错: {e}")
                
                # 记录获取到的趋势数据
                logger.info(f"获取到电影 {movie_id} 的评分趋势数据: {len(rating_trends)} 条")
                
            except Exception as e:
                logger.error(f"获取评分趋势数据失败: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
            # 将数据转换为JSON字符串，确保可以安全传递到模板
            import json
            
            # 添加到上下文
            if comment_keywords:
                # 确保数据类型正确
                if not isinstance(comment_keywords, list):
                    logger.warning(f"评论关键词数据类型不是列表，而是 {type(comment_keywords)}")
                    if isinstance(comment_keywords, dict) and 'keywords' in comment_keywords and isinstance(comment_keywords['keywords'], list):
                        comment_keywords = comment_keywords['keywords']
                        logger.info("已从字典中提取关键词列表")
                
                # 记录数据样本以便调试
                if comment_keywords and len(comment_keywords) > 0:
                    sample = comment_keywords[0] if len(comment_keywords) > 0 else None
                    logger.info(f"关键词数据样本: {sample}")
                
                try:
                    context['comment_keywords'] = json.dumps(comment_keywords)
                    logger.info(f"成功添加词云数据到上下文: {len(comment_keywords)} 个关键词")
                except (TypeError, ValueError) as e:
                    logger.error(f"序列化词云数据失败: {e}")
                    # 尝试修复数据
                    fixed_keywords = []
                    for item in comment_keywords:
                        if isinstance(item, dict) and ('name' in item or 'word' in item) and ('value' in item or 'weight' in item):
                            name = item.get('name', item.get('word', ''))
                            value = item.get('value', item.get('weight', 1))
                            fixed_keywords.append({'name': str(name), 'value': float(value) if isinstance(value, (int, float)) else 1})
                    
                    context['comment_keywords'] = json.dumps(fixed_keywords)
                    logger.info(f"修复后的词云数据: {len(fixed_keywords)} 个关键词")
            
            # 添加策略词云数据到上下文
            try:
                context['sequential_wordcloud'] = json.dumps(sequential_wordcloud)
                context['random_pages_wordcloud'] = json.dumps(random_pages_wordcloud)
                context['random_interval_wordcloud'] = json.dumps(random_interval_wordcloud)
                context['random_block_wordcloud'] = json.dumps(random_block_wordcloud)
                logger.info("成功添加策略词云数据到上下文")
            except (TypeError, ValueError) as e:
                logger.error(f"序列化策略词云数据失败: {e}")
            
            # 添加评分趋势数据到上下文
            if rating_trends:
                try:
                    context['rating_trends'] = json.dumps(rating_trends)
                    logger.info(f"成功添加评分趋势数据到上下文: {len(rating_trends)} 个数据点")
                except (TypeError, ValueError) as e:
                    logger.error(f"序列化评分趋势数据失败: {e}")
            
            # 记录获取到的数据
            logger.info(f"已完成电影 {movie_id} 的数据获取和处理")
            
            # 如果没有任何词云数据，触发异步处理以生成数据
            if not any([comment_keywords, sequential_wordcloud, random_pages_wordcloud, 
                         random_interval_wordcloud, random_block_wordcloud]):
                logger.warning(f"电影 {movie_id} 没有任何词云数据，触发异步处理")
                threading.Thread(
                    target=process_comment_analysis_async,
                    args=(movie_id,)
                ).start()
            
        except Exception as e:
            logger.error(f"获取MongoDB数据失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # 返回详情页面，包含电影信息和词云数据
        return render(request, 'douban_detail.html', context)
        
    except Movie.DoesNotExist:
        logger.error(f"电影 {movie_id} 不存在")
        return render(request, 'error.html', {'error_message': '电影不存在'})
    except Exception as e:
        logger.error(f"电影详情页加载失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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


@csrf_protect
@require_http_methods(["POST"])
def update_movie_wordcloud(request, movie_id):
    """
    更新电影评论词云数据
    """
    try:
        # 记录开始时间
        start_time = time.time()
        logger.info(f"开始更新电影 {movie_id} 的评论词云")

        # 连接MongoDB
        mongo_client = MongoDBClient()

        # 查找电影信息
        movie = Movie.objects.filter(douban_id=movie_id).first()
        if not movie:
            logger.error(f"未找到电影 {movie_id}")
            return JsonResponse({
                'success': False,
                'message': f"未找到ID为 {movie_id} 的电影"
            })

        # 重新生成词云数据
        wordcloud_data = mongo_client.generate_wordcloud_data(movie_id)
        if not wordcloud_data:
            # 如果无法生成新的词云数据，尝试获取已有的数据
            wordcloud_data = mongo_client.get_comment_keywords(movie_id)

        # 生成各种策略的词云数据
        strategy_data = {
            'sequential': mongo_client.generate_strategy_wordcloud(movie_id, 'sequential'),
            'random_pages': mongo_client.generate_strategy_wordcloud(movie_id, 'random_pages'),
            'random_interval': mongo_client.generate_strategy_wordcloud(movie_id, 'random_interval'),
            'random_block': mongo_client.generate_strategy_wordcloud(movie_id, 'random_block'),
            'random': mongo_client.generate_strategy_wordcloud(movie_id, 'random')
        }

        # 如果所有数据都为空，返回示例数据
        if not wordcloud_data:
            # 创建示例数据
            wordcloud_data = generate_sample_wordcloud_data(movie.title)
            logger.warning(f"无法生成真实词云数据，使用示例数据")

        # 记录完成时间
        elapsed_time = time.time() - start_time
        logger.info(f"更新电影 {movie_id} 的评论词云完成，耗时 {elapsed_time:.2f} 秒")

        return JsonResponse({
            'success': True,
            'wordcloud_data': wordcloud_data,
            'strategy_data': strategy_data,
            'elapsed_time': f"{elapsed_time:.2f}"
        })

    except Exception as e:
        logger.exception(f"更新电影 {movie_id} 的评论词云时出错: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f"更新词云时出错: {str(e)}"
        })

@csrf_protect
@require_http_methods(["POST"])
def toggle_movie_published(request):
    """
    切换电影的已发表状态
    """
    try:
        # 添加详细的请求信息日志
        logger.info("===== 收到切换电影发表状态请求 =====")
        logger.info(f"请求方法: {request.method}")
        logger.info(f"请求头: {dict(request.headers)}")
        logger.info(f"表单数据: {dict(request.POST)}")
        logger.info(f"COOKIES: {request.COOKIES}")
        logger.info("================================")
        
        # 获取电影ID
        movie_id = request.POST.get('movie_id')
        logger.info(f"提取的电影ID: {movie_id}")
        
        if not movie_id:
            logger.error("错误: 缺少电影ID参数")
            return JsonResponse({
                'success': False,
                'message': '缺少电影ID参数'
            }, status=400)
            
        # 查找电影
        try:
            logger.info(f"尝试查找电影ID: {movie_id}")
            movie = Movie.objects.get(id=movie_id)
            logger.info(f"找到电影: {movie.title}, 当前发表状态: {movie.is_published}")
        except Movie.DoesNotExist:
            logger.error(f"错误: 电影ID {movie_id} 不存在")
            return JsonResponse({
                'success': False,
                'message': f'电影ID {movie_id} 不存在'
            }, status=404)
            
        # 切换发表状态
        old_state = movie.is_published
        movie.is_published = not movie.is_published
        logger.info(f"电影 {movie.title} 的发表状态从 {old_state} 切换为 {movie.is_published}")
        
        # 保存更改
        movie.save()
        logger.info(f"电影 {movie.title} 的状态已更新并保存到数据库")
        
        # 返回成功响应
        response_data = {
            'success': True,
            'is_published': movie.is_published,
            'message': f'电影 "{movie.title}" 已{"发表" if movie.is_published else "取消发表"}'
        }
        logger.info(f"返回响应: {response_data}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        logger.error(f"处理请求时出现异常: {str(e)}")
        logger.error(traceback.format_exc())
        
        return JsonResponse({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_last_crawl_status(request):
    """获取最近一次IP爬取的状态信息"""
    try:
        # 检查是否有运行中的爬虫任务
        lock_file = os.path.join(settings.BASE_DIR, "crawler.lock")
        is_running = os.path.exists(lock_file)
        
        if is_running:
            # 如果爬虫正在运行，返回进行中状态
            return JsonResponse({
                'success': True,
                'status': 'running',
                'message': 'IP采集任务正在进行中',
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'details': '系统正在爬取新的代理IP，请稍后查看结果。'
            })
        
        # 获取最近添加的IP信息
        last_ip = IpData.objects.order_by('-created_at').first()
        
        if last_ip:
            # 计算距离现在的时间差
            time_diff = timezone.now() - last_ip.created_at
            hours = time_diff.total_seconds() // 3600
            minutes = (time_diff.total_seconds() % 3600) // 60
            
            # 格式化时间差
            time_diff_str = ""
            if hours > 0:
                time_diff_str += f"{int(hours)}小时"
            if minutes > 0 or hours == 0:
                time_diff_str += f"{int(minutes)}分钟"
            if hours == 0 and minutes == 0:
                time_diff_str = "刚刚"
            
            return JsonResponse({
                'success': True,
                'status': 'completed',
                'message': f'最近添加的IP: {last_ip.server}，位于{last_ip.country}',
                'timestamp': last_ip.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'time_ago': time_diff_str,
                'details': f'最近一次IP添加于{time_diff_str}前，服务器地址: {last_ip.server}，国家: {last_ip.country}，类型: {last_ip.type_data}，分数: {last_ip.score}'
            })
        else:
            # 如果没有IP记录
            return JsonResponse({
                'success': True,
                'status': 'unknown',
                'message': '未找到任何IP记录',
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                'details': 'IP池中没有任何记录，请运行采集任务添加IP。'
            })
    except Exception as e:
        logger.error(f"获取爬取状态失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'details': f'获取爬取状态时发生错误: {str(e)}'
        })

@login_required
@require_http_methods(["POST"])
def create_collection(request):
    """创建新合集"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '仅支持POST请求'}, status=405)
    
    try:
        data = json.loads(request.body)
        title = data.get('title')
        collection_type = data.get('collection_type')
        description = data.get('description', '')
        cover_image = data.get('cover_image', '')
        is_published = data.get('is_published', False)
        movie_ids = data.get('movie_ids', [])
        
        # 验证必填字段
        if not title or not collection_type:
            return JsonResponse({'status': 'error', 'message': '标题和类型不能为空'}, status=400)
        
        # 创建合集
        collection = Collection.objects.create(
            title=title,
            collection_type=collection_type,
            description=description,
            cover_image=cover_image,
            is_published=is_published
        )
        
        # 添加关联电影
        if movie_ids and len(movie_ids) > 0:
            movies = Movie.objects.filter(id__in=movie_ids)
            collection.movies.add(*movies)
        
        return JsonResponse({
            'status': 'success', 
            'message': '合集创建成功',
            'data': {'id': collection.id}
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def update_collection(request, collection_id):
    """更新合集信息"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '仅支持POST请求'}, status=405)
    
    try:
        collection = Collection.objects.get(id=collection_id)
        data = json.loads(request.body)
        
        # 更新合集字段
        if 'title' in data:
            collection.title = data['title']
        if 'collection_type' in data:
            collection.collection_type = data['collection_type']
        if 'description' in data:
            collection.description = data['description']
        if 'cover_image' in data:
            collection.cover_image = data['cover_image']
        if 'is_published' in data:
            collection.is_published = data['is_published']
        
        collection.save()
        
        # 更新关联电影
        if 'movie_ids' in data:
            collection.movies.clear()
            if data['movie_ids'] and len(data['movie_ids']) > 0:
                movies = Movie.objects.filter(id__in=data['movie_ids'])
                collection.movies.add(*movies)
        
        return JsonResponse({'status': 'success', 'message': '合集更新成功'})
        
    except Collection.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '合集不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def delete_collection(request, collection_id):
    """删除合集"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '仅支持POST请求'}, status=405)
    
    try:
        collection = Collection.objects.get(id=collection_id)
        collection.delete()
        return JsonResponse({'status': 'success', 'message': '合集删除成功'})
    except Collection.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '合集不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def get_collection(request, collection_id):
    """获取单个合集详情"""
    try:
        collection = Collection.objects.get(id=collection_id)
        # 获取合集关联的电影
        movie_ids = collection.movies.values_list('id', flat=True)
        
        response_data = {
            'id': collection.id,
            'title': collection.title,
            'collection_type': collection.collection_type,
            'description': collection.description,
            'cover_image': collection.cover_image,
            'is_published': collection.is_published,
            'movie_ids': list(movie_ids),
            'created_at': collection.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': collection.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        return JsonResponse({'status': 'success', 'data': response_data})
    except Collection.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '合集不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def get_movies_for_selection(request):
    """获取电影列表用于合集选择"""
    try:
        movies = Movie.objects.all().order_by('-created_at')
        movie_list = []
        
        for movie in movies:
            movie_list.append({
                'id': movie.id,
                'title': movie.title,
                'year': movie.year,
                'rating': movie.rating,
                'cover_image': movie.cover_image
            })
        
        return JsonResponse({'status': 'success', 'movies': movie_list})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def data_analysis(request):
    return render(request, 'wechat.html', {'active_menu': 'data_analysis'})

@login_required
def logs_view(request):
    """日志查看页面"""
    log_files = []
    
    # 路径兼容性处理
    is_windows = os.name == 'nt'
    
    # Django日志目录
    django_log_dir = os.path.join(settings.BASE_DIR, 'logs')
    if os.path.exists(django_log_dir):
        for file in os.listdir(django_log_dir):
            if file.startswith('django') or file.endswith('.log'):
                log_path = os.path.join(django_log_dir, file)
                file_stat = os.stat(log_path)
                size_bytes = file_stat.st_size
                size_display = format_file_size(size_bytes)
                last_modified = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                
                # 检查是否包含错误
                has_error = check_log_for_errors(log_path)
                
                # 确定日志类型
                log_type = 'django'
                description = 'Django系统日志，记录Web应用运行状态'
                
                if 'ip_operator' in file:
                    log_type = 'crawler'
                    description = 'IP爬虫日志，记录IP采集过程'
                
                log_files.append({
                    'name': file,
                    'path': log_path,
                    'size': size_display,
                    'last_modified': last_modified,
                    'type': log_type,
                    'has_error': has_error,
                    'description': description
                })
    
    # 应用日志 - 根据操作系统调整路径
    # Windows: 父目录下的logs
    # Linux: 当前项目目录下的logs
    if is_windows:
        app_log_dir = os.path.join(os.path.dirname(settings.BASE_DIR), 'logs')
    else:
        app_log_dir = django_log_dir  # Linux下使用同一日志目录
        
    if os.path.exists(app_log_dir) and app_log_dir != django_log_dir:
        for file in os.listdir(app_log_dir):
            if file.endswith('.log'):
                log_path = os.path.join(app_log_dir, file)
                file_stat = os.stat(log_path)
                size_bytes = file_stat.st_size
                size_display = format_file_size(size_bytes)
                last_modified = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                
                # 检查是否包含错误
                has_error = check_log_for_errors(log_path)
                
                # 根据文件名确定日志类型
                if 'crawler' in file:
                    log_type = 'crawler'
                    description = 'IP爬虫日志，记录IP采集过程'
                elif 'spider' in file or 'scrapy' in file or 'collectip' in file:
                    log_type = 'spider'
                    description = '爬虫进程日志，记录爬虫运行状态'
                elif 'scheduler' in file:
                    log_type = 'scheduler'
                    description = '调度器日志，记录自动任务执行'
                elif 'douban' in file:
                    log_type = 'douban'
                    description = '豆瓣数据采集日志'
                elif 'scorer' in file:
                    log_type = 'scorer'
                    description = 'IP评分器日志，记录IP评分过程'
                else:
                    log_type = 'other'
                    description = '其他系统日志'
                    
                log_files.append({
                    'name': file,
                    'path': log_path,
                    'size': size_display,
                    'last_modified': last_modified,
                    'type': log_type,
                    'has_error': has_error,
                    'description': description
                })
    
    # 检查Apache日志目录
    apache_log_dirs = ['/var/log/apache2', '/var/log/httpd']
    for apache_dir in apache_log_dirs:
        if os.path.exists(apache_dir):
            for file in os.listdir(apache_dir):
                if 'collectip' in file and file.endswith('.log'):
                    log_path = os.path.join(apache_dir, file)
                    try:
                        file_stat = os.stat(log_path)
                        size_bytes = file_stat.st_size
                        size_display = format_file_size(size_bytes)
                        last_modified = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        
                        # 确定日志类型和描述
                        log_type = 'apache'
                        description = 'Apache服务器日志'
                        if 'error' in file:
                            description = 'Apache错误日志'
                            has_error = True
                        elif 'access' in file:
                            description = 'Apache访问日志'
                            has_error = False
                        
                        log_files.append({
                            'name': file,
                            'path': log_path,
                            'size': size_display,
                            'last_modified': last_modified,
                            'type': log_type,
                            'has_error': has_error,
                            'description': description
                        })
                    except (PermissionError, OSError):
                        # 如果没有权限读取Apache日志，跳过
                        continue
    
    # 按最后修改时间排序，最新的在前面
    log_files.sort(key=lambda x: x['last_modified'], reverse=True)
    
    context = {
        'page_title': '日志查询',
        'log_files': log_files
    }
    return render(request, 'logs.html', context)

@login_required
def get_log_content(request):
    """获取日志内容API"""
    log_path = request.GET.get('path', '')
    
    if not log_path or not os.path.exists(log_path):
        return JsonResponse({
            'status': 'error',
            'message': '日志文件不存在'
        })
    
    try:
        # 检查是否为Apache日志，需要特殊处理权限
        is_apache_log = '/var/log/apache' in log_path or '/var/log/httpd' in log_path
        
        # 判断文件大小，如果过大则只读取尾部内容
        file_size = os.path.getsize(log_path)
        max_size = 1024 * 1024  # 1MB
        
        if is_apache_log and not os.access(log_path, os.R_OK):
            # 对于Apache日志，如果没有直接读取权限，尝试使用系统命令获取
            import subprocess
            try:
                # 使用tail命令获取最后1000行
                process = subprocess.run(['sudo', 'tail', '-n', '1000', log_path], 
                                      capture_output=True, text=True, check=True)
                content = process.stdout
                if not content:
                    content = "日志文件为空或无法读取权限不足的内容"
            except subprocess.CalledProcessError:
                # 如果sudo tail失败，尝试不带sudo
                try:
                    process = subprocess.run(['tail', '-n', '1000', log_path], 
                                          capture_output=True, text=True, check=True)
                    content = process.stdout
                except:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Apache日志文件权限不足，无法读取'
                    })
        else:
            # 常规文件读取处理
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                if file_size > max_size:
                    # 文件过大，只读取尾部
                    f.seek(max_size * -1, os.SEEK_END)
                    # 丢弃第一行，因为可能是不完整的
                    f.readline()
                    content = f.read()
                    content = "... [文件过大，仅显示最后部分] ...\n\n" + content
                else:
                    content = f.read()
        
        return JsonResponse({
            'status': 'success',
            'content': content
        })
    except Exception as e:
        logger.exception(f"读取日志文件失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'读取日志文件失败: {str(e)}'
        })

@login_required
def download_log(request):
    """下载日志文件"""
    log_path = request.GET.get('path', '')
    
    if not log_path or not os.path.exists(log_path):
        return JsonResponse({
            'status': 'error',
            'message': '日志文件不存在'
        })
    
    try:
        filename = os.path.basename(log_path)
        
        # 检查是否为Apache日志，需要特殊处理权限
        is_apache_log = '/var/log/apache' in log_path or '/var/log/httpd' in log_path
        
        if is_apache_log and not os.access(log_path, os.R_OK):
            # 对于Apache日志，如果没有直接读取权限，尝试使用系统命令获取
            import subprocess
            import tempfile
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # 尝试使用sudo复制文件到临时位置
                subprocess.run(['sudo', 'cp', log_path, temp_path], check=True)
                subprocess.run(['sudo', 'chmod', '644', temp_path], check=True)
                
                # 读取临时文件
                with open(temp_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/octet-stream')
                
                # 删除临时文件
                os.unlink(temp_path)
            except subprocess.CalledProcessError:
                # 如果sudo命令失败，返回错误信息
                return JsonResponse({
                    'status': 'error',
                    'message': 'Apache日志文件权限不足，无法下载'
                })
        else:
            # 常规文件处理
            with open(log_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.exception(f"下载日志文件失败: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'下载日志文件失败: {str(e)}'
        })

def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def check_log_for_errors(log_path):
    """检查日志文件是否包含错误"""
    try:
        # 判断文件大小，如果过大则只检查尾部
        file_size = os.path.getsize(log_path)
        check_size = min(file_size, 50 * 1024)  # 最多检查50KB
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            if file_size > check_size:
                f.seek(-check_size, os.SEEK_END)
                # 丢弃第一行，因为可能是不完整的
                f.readline()
            
            for line in f:
                if 'ERROR' in line or 'CRITICAL' in line or 'Exception' in line or 'Error' in line:
                    return True
        
        return False
    except Exception:
        # 如果读取出错，默认返回False
        return False

# 添加CSRF调试视图
@csrf_exempt
def csrf_debug(request):
    """调试CSRF配置的视图"""
    csrf_token = get_token(request)
    debug_info = {
        'csrf_token': csrf_token,
        'headers': dict(request.headers),
        'cookies': dict(request.COOKIES),
        'is_secure': request.is_secure(),
        'method': request.method,
        'path': request.path,
        'host': request.get_host(),
    }
    return JsonResponse(debug_info)

@login_required
def check_crawler_task(request):
    """检查爬虫任务状态"""
    try:
        task_id = request.GET.get('task_id')
        if not task_id:
            return JsonResponse({
                'success': False,
                'error': '任务ID不能为空',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # 检查任务状态
        task_status = check_task_status(task_id)
        
        # 构建状态信息
        status_info = {
            'success': True,
            'task_id': task_id,
            'status': task_status['status'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 如果任务已完成，添加结果
        if task_status['result']:
            status_info['result'] = task_status['result']
            
        return JsonResponse(status_info)
    except Exception as e:
        logger.error(f"检查任务状态失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
