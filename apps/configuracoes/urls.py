from django.urls import path
from . import views

app_name = 'configuracoes'

urlpatterns = [
    path('kpis/', views.kpis, name='kpis'),
]
