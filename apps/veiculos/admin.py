from django.contrib import admin
from .models import Veiculo


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ['placa', 'marca', 'modelo', 'unidade', 'ativo']
    list_filter = ['ativo', 'marca']
    search_fields = ['placa', 'marca', 'modelo']
