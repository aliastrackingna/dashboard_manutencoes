from django.urls import path
from . import views

app_name = 'manutencoes'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('oficinas/', views.oficinas, name='oficinas'),
    path('oficinas/<path:nome>/', views.oficina_detalhe, name='oficina_detalhe'),
    path('<str:numero_os>/', views.detalhe, name='detalhe'),
    path('<str:numero_os>/comparar/', views.comparar_orcamentos, name='comparar_orcamentos'),
]
