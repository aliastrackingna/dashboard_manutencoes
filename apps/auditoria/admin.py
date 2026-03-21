from django.contrib import admin

from .models import LogAuditoria


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ['criado_em', 'usuario', 'tipo', 'descricao']
    list_filter = ['tipo', 'usuario']
    search_fields = ['descricao']
