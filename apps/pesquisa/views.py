from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from apps.manutencoes.models import ItemOrcamento
from apps.manutencoes.normalizacao import construir_chave_item_canonica
from .fts import buscar_itens, get_grupos

PERIODOS = {
    'anual': 'Ano atual',
    '30d': '30 dias',
    '60d': '60 dias',
    '90d': '90 dias',
    '180d': '180 dias',
    '360d': '360 dias',
}

STATUS_PRIORIDADE = {
    'Cancelado': 0,
    'Recusado': 1,
    'Lançado': 2,
    'Executado': 3,
    'Em Execução': 4,
    'Escolhido': 5,
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


def _status_rank(status):
    return STATUS_PRIORIDADE.get(status, 9)


def _termos_busca(q):
    descricao_norm = construir_chave_item_canonica('', '', q)['descricao_normalizada']
    return [termo for termo in descricao_norm.split() if termo]


def _chave_item(item):
    tipo_norm = (item.tipo or '').strip().upper()[:3]
    marca_norm = construir_chave_item_canonica('', '', item.marca)['descricao_normalizada']
    descricao_norm = item.descricao_normalizada

    if not descricao_norm:
        fallback = construir_chave_item_canonica(item.tipo, item.codigo_item, item.descricao)
        descricao_norm = fallback['descricao_normalizada']

    if descricao_norm:
        return f'{tipo_norm}|DESC:{descricao_norm}|MARCA:{marca_norm}'

    if item.chave_item_canonica:
        return item.chave_item_canonica

    fallback = construir_chave_item_canonica(item.tipo, item.codigo_item, item.descricao)
    return fallback['chave_item_canonica']


def _agrupar_resultados(items):
    agrupados = {}

    for item in items:
        chave = _chave_item(item)
        if chave not in agrupados:
            agrupados[chave] = {
                'tipo': item.tipo,
                'codigo_item': item.codigo_item,
                'descricao': item.descricao,
                'marca': item.marca,
                'grupo': item.grupo,
                'ocorrencias': 0,
                'valor_min': item.valor_unit,
                'valor_max': item.valor_unit,
                'valor_soma': Decimal('0'),
                'exemplos_por_os': {},
                'chave_item_canonica': chave,
            }

        grupo = agrupados[chave]
        grupo['ocorrencias'] += 1
        grupo['valor_soma'] += item.valor_unit

        if item.valor_unit < grupo['valor_min']:
            grupo['valor_min'] = item.valor_unit
        if item.valor_unit > grupo['valor_max']:
            grupo['valor_max'] = item.valor_unit

        os_numero = item.orcamento.manutencao.numero_os
        exemplo = {
            'os': os_numero,
            'orcamento': item.orcamento.codigo_orcamento,
            'orcamento_status': item.orcamento.status,
            'valor': item.valor_unit,
            'qtd': item.qtd,
            'data_abertura': item.orcamento.manutencao.data_abertura,
        }
        atual = grupo['exemplos_por_os'].get(os_numero)
        if atual is None:
            grupo['exemplos_por_os'][os_numero] = exemplo
        else:
            candidato = (
                _status_rank(exemplo['orcamento_status']),
                -(exemplo['data_abertura'].timestamp() if exemplo['data_abertura'] else 0),
                -exemplo['orcamento'],
            )
            existente = (
                _status_rank(atual['orcamento_status']),
                -(atual['data_abertura'].timestamp() if atual['data_abertura'] else 0),
                -atual['orcamento'],
            )
            if candidato < existente:
                grupo['exemplos_por_os'][os_numero] = exemplo

    resultados = []
    for grupo in agrupados.values():
        valor_medio = grupo['valor_soma'] / grupo['ocorrencias'] if grupo['ocorrencias'] else Decimal('0')
        exemplos_ordenados = sorted(
            grupo['exemplos_por_os'].values(),
            key=lambda e: (
                -(e['data_abertura'].timestamp() if e['data_abertura'] else 0),
                _status_rank(e['orcamento_status']),
            ),
        )[:5]

        resultados.append({
            'tipo': grupo['tipo'],
            'codigo_item': grupo['codigo_item'],
            'descricao': grupo['descricao'],
            'marca': grupo['marca'],
            'grupo': grupo['grupo'],
            'ocorrencias': grupo['ocorrencias'],
            'valor_min': grupo['valor_min'],
            'valor_max': grupo['valor_max'],
            'valor_medio': valor_medio,
            'chave_item_canonica': grupo['chave_item_canonica'],
            'exemplos': [
                {
                    'os': ex['os'],
                    'orcamento': ex['orcamento'],
                    'orcamento_status': ex['orcamento_status'],
                    'valor': ex['valor'],
                    'qtd': ex['qtd'],
                }
                for ex in exemplos_ordenados
            ],
        })

    resultados.sort(key=lambda r: (-r['ocorrencias'], r['descricao']))
    return resultados


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

        if item_ids or q:
            if q:
                termos = _termos_busca(q)
                filtro_termos = Q()
                for termo in termos:
                    filtro_campo = (
                        Q(descricao_normalizada__icontains=termo)
                        | Q(codigo_item_normalizado__icontains=termo)
                        | Q(marca__icontains=termo)
                        | Q(descricao__icontains=termo)
                        | Q(codigo_item__icontains=termo)
                    )
                    filtro_termos &= filtro_campo

                if item_ids:
                    items_qs = ItemOrcamento.objects.filter(Q(id__in=item_ids) | filtro_termos)
                else:
                    items_qs = ItemOrcamento.objects.filter(filtro_termos)
            else:
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

            items = list(
                items_qs.select_related('orcamento__manutencao').order_by(
                    '-orcamento__manutencao__data_abertura',
                    '-orcamento__codigo_orcamento',
                    '-id',
                )
            )
            resultados = _agrupar_resultados(items)

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
