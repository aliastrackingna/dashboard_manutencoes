from django.urls import path
from . import views

app_name = 'pesquisa'

urlpatterns = [
    path('itens/', views.itens, name='itens'),
]
