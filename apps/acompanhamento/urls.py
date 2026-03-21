from django.urls import path

from . import views

app_name = 'acompanhamento'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('toggle/<str:numero_os>/', views.toggle, name='toggle'),
    path('<int:pk>/editar/', views.editar, name='editar'),
]
