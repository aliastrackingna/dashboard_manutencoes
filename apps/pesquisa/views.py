from datetime import timedelta

from django.shortcuts import render
from django.db.models import Count, Min, Max, Avg
from django.utils import timezone

from apps.manutencoes.models import ItemOrcamento
from .fts import buscar_itens, get_grupos

PERIODOS = {
    'anual': 'Ano atual',
    '30d': '30 dias',
    '60d': '60 dias',
    '90d': '90 dias',
    '180d': '180 dias',
    '360d': '360 dias',
}


def _get_data_inicio(periodo):
    hoje = timezone.now()
    if periodo == '30d':
        return hoje - timedelta(days=30)
    if periodo == '60d':
        return hoje - timedelta(days=60)
    if periodo == '90d':
        return hoje - timedelta(days=90)
    if periodo == '180d':
        return hoje - timedelta(days=180)
    if periodo == '360d':
        return hoje - timedelta(days=360)
    # anual (default)
    return hoje.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


def itens(request):
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    grupo = request.GET.get('grupo', '')
    periodo = request.GET.get('periodo', '')
    aprovado = request.GET.get('aprovado', '')

    resultados = []
    grupos_disponiveis = get_grupos()

    if q or tipo:
        resultados_fts = buscar_itens(q, tipo=tipo if tipo else None)
        item_ids = [r['item_id'] for r in resultados_fts]

        if item_ids:
            # Aggregate results by description
            items_qs = ItemOrcamento.objects.filter(id__in=item_ids)
            if aprovado:
                items_qs = items_qs.filter(
                    orcamento__status__in=['Escolhido', 'Executado', 'Em Execução'],
                )
            if grupo:
                items_qs = items_qs.filter(grupo=grupo)
            if periodo:
                data_inicio = _get_data_inicio(periodo)
                items_qs = items_qs.filter(orcamento__manutencao__data_abertura__gte=data_inicio)

            agrupados = (
                items_qs
                .values('descricao', 'marca', 'tipo', 'grupo', 'codigo_item')
                .annotate(
                    ocorrencias=Count('id'),
                    valor_min=Min('valor_unit'),
                    valor_max=Max('valor_unit'),
                    valor_medio=Avg('valor_unit'),
                )
                .order_by('-ocorrencias')
            )

            for item in agrupados:
                sample_qs = items_qs.filter(
                    descricao=item['descricao'],
                    marca=item['marca'],
                    tipo=item['tipo'],
                    grupo=item['grupo'],
                    codigo_item=item['codigo_item'],
                )
                sample_items = (
                    sample_qs
                    .select_related('orcamento__manutencao')
                    .order_by('-orcamento__manutencao__data_abertura')[:5]
                )

                item['exemplos'] = [
                    {
                        'os': si.orcamento.manutencao.numero_os,
                        'orcamento': si.orcamento.codigo_orcamento,
                        'orcamento_status': si.orcamento.status,
                        'valor': si.valor_unit,
                        'qtd': si.qtd,
                    }
                    for si in sample_items
                ]
                resultados.append(item)

    return render(request, 'pesquisa/itens.html', {
        'q': q,
        'tipo': tipo,
        'grupo': grupo,
        'periodo': periodo,
        'periodos': PERIODOS,
        'aprovado': aprovado,
        'resultados': resultados,
        'grupos_disponiveis': grupos_disponiveis,
    })
