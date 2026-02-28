from django.contrib import admin
from .models import KPIConfig


@admin.register(KPIConfig)
class KPIConfigAdmin(admin.ModelAdmin):
    list_display = ['chave', 'descricao', 'valor', 'unidade', 'atualizado_em']
    search_fields = ['chave', 'descricao']
