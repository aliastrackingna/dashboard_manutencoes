from django.urls import path
from . import views

app_name = 'multas'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('nova/', views.criar, name='criar'),
    path('<str:auto_infracao>/editar/', views.editar, name='editar'),
]
