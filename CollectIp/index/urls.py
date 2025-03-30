# 豆瓣数据相关路由
path('douban/', views.douban, name='douban'),  # 豆瓣首页，会重定向到概览
path('douban/overview/', views.douban_overview, name='douban_overview'),
path('douban/movies/', views.movie_list, name='movie_list'),
path('douban/tv/', views.tv_list, name='tv_list'),
path('douban/trends/', views.data_trend, name='data_trend'),
path('douban/settings/', views.douban_settings, name='douban_settings'),
# 电影采集API
path('crawl_movie/', views.crawl_movie_view, name='crawl_movie'),
path('douban/movie/<int:movie_id>/comments/', movie_comment_analysis, name='movie_comment_analysis'),
path('api/trigger-comment-processing/', trigger_comment_processing, name='trigger_comment_processing'), 