from django.contrib import admin
from .models import ConfigGeral, KPIConfig


@admin.register(KPIConfig)
class KPIConfigAdmin(admin.ModelAdmin):
    list_display = ['chave', 'descricao', 'valor', 'unidade', 'atualizado_em']
    search_fields = ['chave', 'descricao']


@admin.register(ConfigGeral)
class ConfigGeralAdmin(admin.ModelAdmin):
    list_display = ['chave', 'valor', 'descricao', 'atualizado_em']
    search_fields = ['chave', 'descricao']
