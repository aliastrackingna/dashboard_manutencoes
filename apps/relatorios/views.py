from django.db.models import Sum
from django.shortcuts import render

from apps.manutencoes.models import Manutencao

MESES_PT = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro',
}


def _calcular_atraso(os):
    """Retorna True (atraso), False (no prazo) ou None (sem dados de previsão)."""
    if not os.inicio_execucao or not os.fim_execucao:
        return None
    orcamento = os.orcamentos.filter(
        status='Executado', previsao_em_dias__gt=0,
    ).first()
    if not orcamento:
        return None
    dias_execucao = (os.fim_execucao - os.inicio_execucao).total_seconds() / 86400
    return dias_execucao > orcamento.previsao_em_dias


def index(request):
    meses_datas = (
        Manutencao.objects
        .filter(status='Executada', data_integracao__isnull=False)
        .dates('data_integracao', 'month', order='DESC')
    )
    meses_disponiveis = [
        {
            'valor': d.strftime('%Y-%m'),
            'label': f'{MESES_PT[d.month]}/{d.year}',
        }
        for d in meses_datas
    ]

    mes_selecionado = request.GET.get('mes', '')
    ordens = []
    valor_total_soma = 0

    if mes_selecionado:
        try:
            ano, mes = mes_selecionado.split('-')
            ano, mes = int(ano), int(mes)
        except (ValueError, AttributeError):
            ano, mes = None, None

        if ano and mes:
            qs = (
                Manutencao.objects
                .filter(
                    status='Executada',
                    data_integracao__year=ano,
                    data_integracao__month=mes,
                )
                .select_related('veiculo')
                .prefetch_related('orcamentos')
            )
            for os_obj in qs:
                ordens.append({
                    'os': os_obj,
                    'em_atraso': _calcular_atraso(os_obj),
                })
            valor_total_soma = qs.aggregate(total=Sum('valor_total'))['total'] or 0

    return render(request, 'relatorios/index.html', {
        'meses_disponiveis': meses_disponiveis,
        'ordens': ordens,
        'mes_selecionado': mes_selecionado,
        'valor_total_soma': valor_total_soma,
    })
