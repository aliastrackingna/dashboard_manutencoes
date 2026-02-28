from django.contrib import admin
from .models import Manutencao, Orcamento, ItemOrcamento


class OrcamentoInline(admin.TabularInline):
    model = Orcamento
    extra = 0


class ItemOrcamentoInline(admin.TabularInline):
    model = ItemOrcamento
    extra = 0


@admin.register(Manutencao)
class ManutencaoAdmin(admin.ModelAdmin):
    list_display = ['numero_os', 'veiculo', 'status', 'data_abertura', 'valor_total']
    list_filter = ['status', 'setor']
    search_fields = ['numero_os', 'descricao']
    inlines = [OrcamentoInline]


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ['codigo_orcamento', 'manutencao', 'oficina', 'valor', 'status']
    list_filter = ['status']
    search_fields = ['codigo_orcamento', 'oficina']
    inlines = [ItemOrcamentoInline]
