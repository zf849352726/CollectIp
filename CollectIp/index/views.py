from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from .models import IpData, Movie, ProxySettings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging
from ip_operator.services.crawler import start_crawl, start_douban_crawl
from ip_operator.services.scorer import start_score
import threading

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
                'min_score': 10
            }
        )
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'data': {
                    'crawler_interval': settings.crawler_interval,
                    'score_interval': settings.score_interval,
                    'min_score': settings.min_score
                }
            })
        
        elif request.method == 'POST':
            try:
                crawler_interval = int(request.POST.get('crawler_interval', 0))
                score_interval = int(request.POST.get('score_interval', 0))
                min_score = int(request.POST.get('min_score', 0))
                
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
                settings.save()
                
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
def douban_view(request):
    # 从数据库获取数据
    movies = Movie.objects.all()
    
    # 添加分页
    page = request.GET.get('page', 1)
    paginator = Paginator(movies, 10)  # 每页显示10条数据
    movies = paginator.get_page(page)
    
    context = {
        'active_menu': 'movie_list',
        'page_title': '电影列表',
        'movies': movies
    }
    return render(request, 'douban.html', context)

@login_required
def douban_overview(request):
    return render(request, 'douban.html', {'active_menu': 'douban_overview'})

@login_required
def movie_list(request):
    return render(request, 'douban.html', {'active_menu': 'movie_list'})

@login_required
def tv_list(request):
    return render(request, 'douban.html', {'active_menu': 'tv_list'})

@login_required
def data_trend(request):
    return render(request, 'douban.html', {'active_menu': 'data_trend'})

@login_required
def douban_settings(request):
    return render(request, 'douban.html', {'active_menu': 'douban_settings'})

@login_required
@require_http_methods(["POST"])
def crawl_movie_view(request):
    """接收电影名称并启动豆瓣爬虫"""
    import json
    from ip_operator.services.crawler import start_douban_crawl
    
    try:
        # 从请求体获取电影名称
        data = json.loads(request.body)
        movie_name = data.get('movie_name')
        
        if not movie_name:
            return JsonResponse({
                'success': False,
                'error': '电影名称不能为空'
            })
            
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
            return JsonResponse({
                'success': False,
                'error': '爬虫启动失败，请查看日志'
            })
    except Exception as e:
        logger.error(f"启动电影采集失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
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



