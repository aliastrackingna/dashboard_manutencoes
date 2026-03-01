from django.shortcuts import render
from django.http import JsonResponse
from django.core.paginator import Paginator
from apps.manutencoes.models import Manutencao
from apps.veiculos.models import Veiculo
from .kpis import get_periodo, calcular_kpis, dados_graficos


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
    return render(request, 'dashboard/index.html', {
        'kpis': kpis,
        'graficos': graficos,
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
