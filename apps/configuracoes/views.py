from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect
from django.contrib import messages

from apps.auditoria.models import LogAuditoria
from .models import KPIConfig


DEFAULT_KPIS = [
    {'chave': 'custo_maximo_os', 'descricao': 'Custo máximo aceitável por OS', 'valor': 5000, 'unidade': 'R$'},
    {'chave': 'sla_dias_execucao', 'descricao': 'SLA de dias para execução', 'valor': 15, 'unidade': 'dias'},
    {'chave': 'meta_prazo_pct', 'descricao': 'Meta de OS dentro do prazo', 'valor': 80, 'unidade': '%'},
    {'chave': 'ticket_medio_alerta', 'descricao': 'Ticket médio para alerta', 'valor': 3000, 'unidade': 'R$'},
]


def kpis(request):
    # Ensure defaults exist
    for kpi in DEFAULT_KPIS:
        KPIConfig.objects.get_or_create(
            chave=kpi['chave'],
            defaults=kpi,
        )

    if request.method == 'POST':
        alteracoes = []
        for kpi in KPIConfig.objects.all():
            novo_valor = request.POST.get(f'valor_{kpi.id}')
            if novo_valor is not None:
                try:
                    valor_anterior = kpi.valor
                    kpi.valor = Decimal(novo_valor.replace(',', '.'))
                    if kpi.valor != valor_anterior:
                        alteracoes.append(
                            f'{kpi.descricao} alterado de {valor_anterior} {kpi.unidade}'
                            f' para {kpi.valor} {kpi.unidade}'
                        )
                    kpi.save()
                except (InvalidOperation, ValueError):
                    messages.error(request, f'Valor inválido para "{kpi.descricao}".')
        for desc in alteracoes:
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo='ALTERACAO',
                descricao=desc,
            )
        messages.success(request, 'Configurações de KPI atualizadas.')
        return redirect('configuracoes:kpis')

    kpis_list = KPIConfig.objects.all().order_by('chave')
    return render(request, 'configuracoes/kpis.html', {'kpis': kpis_list})
