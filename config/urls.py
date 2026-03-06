from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda r: redirect('dashboard:index')),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', include('apps.dashboard.urls')),
    path('veiculos/', include('apps.veiculos.urls')),
    path('manutencoes/', include('apps.manutencoes.urls')),
    path('importacao/', include('apps.importacao.urls')),
    path('pesquisa/', include('apps.pesquisa.urls')),
    path('configuracoes/', include('apps.configuracoes.urls')),
    path('multas/', include('apps.multas.urls')),
    path('relatorios/', include('apps.relatorios.urls')),
]
