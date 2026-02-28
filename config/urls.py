from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda r: redirect('dashboard:index')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('veiculos/', include('apps.veiculos.urls')),
    path('manutencoes/', include('apps.manutencoes.urls')),
    path('importacao/', include('apps.importacao.urls')),
    path('pesquisa/', include('apps.pesquisa.urls')),
    path('configuracoes/', include('apps.configuracoes.urls')),
]
