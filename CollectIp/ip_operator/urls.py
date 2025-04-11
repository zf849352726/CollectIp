from django.urls import path
from . import views

urlpatterns = [
    path('movies/delete/', views.delete_movie, name='delete_movie'),
] 