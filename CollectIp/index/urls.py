# 微信管理相关路由
path('wechat/overview/', views.wechat_overview, name='wechat_overview'),
path('wechat/article_manage/', views.article_manage, name='article_manage'),
path('wechat/media_library/', views.media_library, name='media_library'),
path('wechat/data_analysis/', views.data_analysis, name='data_analysis'),

# 合集管理相关API
path('api/collections/create/', views.create_collection, name='create_collection'),
path('api/collections/<int:collection_id>/', views.get_collection, name='get_collection'),
path('api/collections/<int:collection_id>/update/', views.update_collection, name='update_collection'),
path('api/collections/<int:collection_id>/delete/', views.delete_collection, name='delete_collection'),
path('api/movies/selection/', views.get_movies_for_selection, name='get_movies_for_selection'),

# 日志管理相关路由
path('logs/', views.logs_view, name='logs_view'),
path('api/logs/content/', views.get_log_content, name='get_log_content'),
path('api/logs/download/', views.download_log, name='download_log'), 