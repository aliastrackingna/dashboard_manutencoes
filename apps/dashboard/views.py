import csv
import json

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from django.utils.safestring import mark_safe

from apps.configuracoes.models import KPIConfig
from apps.manutencoes.models import Manutencao
from apps.veiculos.models import Veiculo
from .kpis import get_periodo, calcular_kpis, dados_graficos


# KPIs onde menor = melhor (threshold invertido)
_MENOR_MELHOR = {'ticket_medio', 'tempo_medio_dias', 'custo_por_veiculo',
                 'total_os', 'valor_total_executado', 'valor_aprovado_executado'}


def _calcular_thresholds(kpis):
    """Retorna dict {chave_kpi: classe_css} baseado nos thresholds do KPIConfig."""
    configs = {c.chave: float(c.valor) for c in KPIConfig.objects.all()}
    resultado = {}
    for chave, valor in kpis.items():
        if chave in ('tendencias',) or not isinstance(valor, (int, float)):
            continue
        threshold = configs.get(chave)
        if threshold is None:
            resultado[chave] = ''
            continue
        if chave in _MENOR_MELHOR:
            if valor <= threshold:
                resultado[chave] = 'border-green-500'
            else:
                resultado[chave] = 'border-red-500'
        else:
            if valor >= threshold:
                resultado[chave] = 'border-green-500'
            else:
                resultado[chave] = 'border-red-500'
    return resultado


def _get_unidade(request):
    """Retorna (unidade_para_filtro, unidade_param_raw).
    unidade_para_filtro: None (todas), '' (sem unidade), ou string com nome.
    unidade_param_raw: valor cru do query param para repassar ao template.
    """
    unidade_param = request.GET.get('unidade', '')
    if unidade_param == '__sem__':
        return '', unidade_param
    elif unidade_param:
        return unidade_param, unidade_param
    return None, unidade_param


def _lista_unidades():
    return list(
        Veiculo.objects.exclude(unidade='')
        .values_list('unidade', flat=True)
        .distinct()
        .order_by('unidade')
    )


def index(request):
    inicio, fim, periodo = get_periodo(request)
    unidade, unidade_param = _get_unidade(request)
    kpis = calcular_kpis(inicio, fim, unidade=unidade)
    graficos = dados_graficos(inicio, fim, unidade=unidade)
    thresholds = _calcular_thresholds(kpis)
    return render(request, 'dashboard/index.html', {
        'kpis': kpis,
        'graficos': graficos,
        'graficos_json': mark_safe(json.dumps(graficos)),
        'thresholds': thresholds,
        'periodo': periodo,
        'inicio': inicio,
        'fim': fim,
        'unidades': _lista_unidades(),
        'unidade_param': unidade_param,
    })


def api_kpis(request):
    inicio, fim, periodo = get_periodo(request)
    unidade, unidade_param = _get_unidade(request)
    kpis = calcular_kpis(inicio, fim, unidade=unidade)
    return JsonResponse(kpis)


def api_graficos(request):
    inicio, fim, periodo = get_periodo(request)
    unidade, unidade_param = _get_unidade(request)
    graficos = dados_graficos(inicio, fim, unidade=unidade)
    return JsonResponse(graficos)


def lista_drilldown(request):
    inicio, fim, periodo = get_periodo(request)
    unidade, unidade_param = _get_unidade(request)

    qs = Manutencao.objects.filter(data_abertura__lte=fim)
    if inicio is not None:
        qs = qs.filter(data_abertura__gte=inicio)
    if unidade is not None:
        qs = qs.filter(veiculo__unidade=unidade)

    filtro = request.GET.get('filtro', '')
    valor = request.GET.get('valor', '')
    titulo = 'Manutenções'

    if filtro == 'status' and valor:
        qs = qs.filter(status=valor)
        titulo = f'OS — {valor}'
    elif filtro == 'setor' and valor:
        qs = qs.filter(setor=valor)
        titulo = f'OS — Setor: {valor}'
    elif filtro == 'veiculo' and valor:
        qs = qs.filter(veiculo__placa=valor)
        titulo = f'OS — Veículo: {valor}'
    elif filtro == 'unidade' and valor:
        qs = qs.filter(veiculo__unidade=valor)
        titulo = f'OS — Unidade: {valor}'
    elif filtro == 'mes' and valor:
        try:
            from datetime import datetime as dt
            mes_dt = dt.strptime(valor, '%b/%Y')
            qs = qs.filter(
                data_abertura__month=mes_dt.month,
                data_abertura__year=mes_dt.year,
            )
            titulo = f'OS — {valor}'
        except ValueError:
            pass

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/lista.html', {
        'page': page,
        'titulo': titulo,
        'filtro': filtro,
        'valor': valor,
        'periodo': periodo,
        'unidade_param': unidade_param,
    })


def exportar_csv(request):
    """Exporta OS filtradas como arquivo CSV."""
    inicio, fim, periodo = get_periodo(request)
    unidade, _ = _get_unidade(request)

    qs = Manutencao.objects.select_related('veiculo').filter(data_abertura__lte=fim)
    if inicio is not None:
        qs = qs.filter(data_abertura__gte=inicio)
    if unidade is not None:
        qs = qs.filter(veiculo__unidade=unidade)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="manutencoes.csv"'
    response.write('\ufeff')  # BOM para Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['OS', 'Placa', 'Unidade', 'Setor', 'Status', 'Abertura', 'Encerramento', 'Valor Total'])

    for m in qs.iterator():
        writer.writerow([
            m.numero_os,
            m.veiculo.placa,
            m.veiculo.unidade or '',
            m.setor or '',
            m.status,
            m.data_abertura.strftime('%d/%m/%Y') if m.data_abertura else '',
            m.data_encerramento.strftime('%d/%m/%Y') if m.data_encerramento else '',
            str(m.valor_total or '0'),
        ])

    return response
