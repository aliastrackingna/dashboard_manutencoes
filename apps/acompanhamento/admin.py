from django.contrib import admin

from .models import Acompanhamento


@admin.register(Acompanhamento)
class AcompanhamentoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'manutencao', 'motivo', 'prioridade', 'finalizado', 'criado_em']
    list_filter = ['motivo', 'prioridade', 'finalizado']
    search_fields = ['manutencao__numero_os']
