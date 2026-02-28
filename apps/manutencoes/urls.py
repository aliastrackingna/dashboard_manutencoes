from django.urls import path
from . import views

app_name = 'manutencoes'

urlpatterns = [
    path('<str:numero_os>/', views.detalhe, name='detalhe'),
    path('<str:numero_os>/comparar/', views.comparar_orcamentos, name='comparar_orcamentos'),
]
