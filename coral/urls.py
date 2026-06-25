from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('register/', views.UserCreateView.as_view(), name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('sobre/', views.sobre, name='sobre'),
    path('contato/', views.ContatoView.as_view(), name='contato'),
    path('contato/sucesso/', views.contato_success, name='contato-success'),
    path('relatos/', views.RelatosListView.as_view(), name='relatos-list'),
    path('relatos/<int:pk>/editar/', views.RelatosUpdateView.as_view(), name='relatos-edit'),
    path('relatos/<int:pk>/deletar/', views.relatos_delete, name='relatos-delete'),
    path('getMediaMes/', views.getMediaMes, name='getMediaMes'),
    path('getDadosDia/', views.getDadosDia, name='getDadosDia'),
    path('getMediaDetalhes/', views.getMediaDetalhes, name='getMediaDetalhes'),
    path('users/create/', views.UserCreateView.as_view(), name='user-create'),
    path('users/update/', views.UserUpdateView.as_view(), name='user-update'),
    path('users/delete/', views.UserDeleteView.as_view(), name='user-delete'),

    # Alertas CRUD
    path('alertas/', views.AlertaListView.as_view(), name='alerta-list'),
    path('alertas/criar/', views.AlertaCreateView.as_view(), name='alerta-create'),
    path('alertas/<int:pk>/editar/', views.AlertaUpdateView.as_view(), name='alerta-update'),
    path('alertas/<int:pk>/deletar/', views.AlertaDeleteView.as_view(), name='alerta-delete'),
    path('alertas/api/criar/', views.criar_alerta_api, name='alerta-criar-api'),
    path('alertas/api/regioes/', views.alertas_regioes_api, name='alerta-regioes-api'),
    path('alertas/api/', views.alertas_api, name='alerta-api'),
    path('alertas/api/<int:pk>/', views.alerta_api_detail, name='alerta-api-detail'),
]