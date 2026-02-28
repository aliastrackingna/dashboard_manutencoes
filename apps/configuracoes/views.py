from django.shortcuts import render, redirect
from django.contrib import messages
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
        for kpi in KPIConfig.objects.all():
            novo_valor = request.POST.get(f'valor_{kpi.id}')
            if novo_valor is not None:
                try:
                    from decimal import Decimal, InvalidOperation
                    kpi.valor = Decimal(novo_valor.replace(',', '.'))
                    kpi.save()
                except (InvalidOperation, ValueError):
                    messages.error(request, f'Valor inválido para "{kpi.descricao}".')
        messages.success(request, 'Configurações de KPI atualizadas.')
        return redirect('configuracoes:kpis')

    kpis_list = KPIConfig.objects.all().order_by('chave')
    return render(request, 'configuracoes/kpis.html', {'kpis': kpis_list})
