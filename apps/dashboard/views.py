from django.shortcuts import render
from django.http import JsonResponse
from django.core.paginator import Paginator
from apps.manutencoes.models import Manutencao
from .kpis import get_periodo, calcular_kpis, dados_graficos


def index(request):
    inicio, fim, periodo = get_periodo(request)
    kpis = calcular_kpis(inicio, fim)
    graficos = dados_graficos(inicio, fim)
    return render(request, 'dashboard/index.html', {
        'kpis': kpis,
        'graficos': graficos,
        'periodo': periodo,
        'inicio': inicio,
        'fim': fim,
    })


def api_kpis(request):
    inicio, fim, periodo = get_periodo(request)
    kpis = calcular_kpis(inicio, fim)
    return JsonResponse(kpis)


def api_graficos(request):
    inicio, fim, periodo = get_periodo(request)
    graficos = dados_graficos(inicio, fim)
    return JsonResponse(graficos)


def lista_drilldown(request):
    inicio, fim, periodo = get_periodo(request)
    qs = Manutencao.objects.filter(data_abertura__gte=inicio, data_abertura__lte=fim)

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
    })
