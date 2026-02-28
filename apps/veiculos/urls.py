from django.urls import path
from . import views

app_name = 'veiculos'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.criar, name='criar'),
    path('<str:placa>/', views.detalhe, name='detalhe'),
    path('<str:placa>/editar/', views.editar, name='editar'),
    path('api/autocomplete/', views.autocomplete, name='autocomplete'),
]
