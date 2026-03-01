from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('lista/', views.lista_drilldown, name='lista'),
    path('exportar/', views.exportar_csv, name='exportar_csv'),
    path('api/kpis/', views.api_kpis, name='api_kpis'),
    path('api/graficos/', views.api_graficos, name='api_graficos'),
]
