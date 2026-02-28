from django.urls import path
from . import views

app_name = 'importacao'

urlpatterns = [
    path('', views.upload, name='upload'),
]
