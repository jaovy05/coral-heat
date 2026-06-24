from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('login/', auth_views.LoginView.as_view(template_name='user_form.html'), name='login'),
    path('sobre/', views.sobre, name='sobre'),
    path('getMediaMes/', views.getMediaMes, name='getMediaMes'),
    path('getDadosDia/', views.getDadosDia, name='getDadosDia'),
    path('getMediaDetalhes/', views.getMediaDetalhes, name='getMediaDetalhes'),
    path('users/create/', views.UserCreateView.as_view(), name='user-create'),
    path('users/update/', views.UserUpdateView.as_view(), name='user-update'),
    path('users/delete/', views.UserDeleteView.as_view(), name='user-delete'),

]