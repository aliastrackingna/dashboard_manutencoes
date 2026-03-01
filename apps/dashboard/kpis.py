from datetime import datetime, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone

from apps.manutencoes.models import Manutencao, Orcamento, ItemOrcamento

CACHE_TIMEOUT = 600  # 10 minutos


def get_periodo(request):
    periodo = request.GET.get('periodo', 'anual')
    hoje = timezone.now()

    if periodo == 'todos':
        inicio = None
        fim = hoje
    elif periodo == '30d':
        inicio = hoje - timedelta(days=30)
        fim = hoje
    elif periodo == '60d':
        inicio = hoje - timedelta(days=60)
        fim = hoje
    elif periodo == '90d':
        inicio = hoje - timedelta(days=90)
        fim = hoje
    elif periodo == '180d':
        inicio = hoje - timedelta(days=180)
        fim = hoje
    elif periodo == '360d':
        inicio = hoje - timedelta(days=360)
        fim = hoje
    elif periodo == 'custom':
        try:
            inicio = timezone.make_aware(datetime.strptime(request.GET.get('inicio', ''), '%Y-%m-%d'))
            fim = timezone.make_aware(datetime.strptime(request.GET.get('fim', ''), '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        except (ValueError, TypeError):
            inicio = hoje.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            fim = hoje
    else:  # anual
        inicio = hoje.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        fim = hoje

    return inicio, fim, periodo


def _filtrar_qs(qs, inicio, fim, unidade=None):
    if inicio is not None:
        qs = qs.filter(data_abertura__gte=inicio)
    qs = qs.filter(data_abertura__lte=fim)
    if unidade is not None:
        qs = qs.filter(veiculo__unidade=unidade)
    return qs


def _periodo_anterior(inicio, fim):
    """Calcula o período equivalente anterior (mesma duração, imediatamente antes)."""
    if inicio is None:
        return None, None
    duracao = fim - inicio
    return inicio - duracao, inicio


def _calcular_kpis_raw(inicio, fim, unidade=None):
    """Calcula KPIs sem tendências (usado internamente para comparação)."""
    qs = _filtrar_qs(Manutencao.objects, inicio, fim, unidade)

    total_os = qs.count()
    executadas = qs.filter(status='Executada')
    valor_total_executado = executadas.aggregate(s=Sum('valor_total'))['s'] or Decimal('0')
    total_executadas = executadas.count()
    ticket_medio = valor_total_executado / total_executadas if total_executadas > 0 else Decimal('0')

    aprovado_executado = qs.filter(
        status__in=['Autorizada Execução', 'Em Execução', 'Executada']
    ).aggregate(s=Sum('valor_total'))['s'] or Decimal('0')

    com_prazo = executadas.filter(
        data_encerramento__isnull=False,
        data_previsao__isnull=False,
    )
    dentro_prazo = com_prazo.filter(data_encerramento__lte=F('data_previsao')).count()
    total_com_prazo = com_prazo.count()
    pct_prazo = round(dentro_prazo / total_com_prazo * 100, 1) if total_com_prazo > 0 else 0

    resolvidas = executadas.filter(data_encerramento__isnull=False)
    if resolvidas.exists():
        tempos = [(m.data_encerramento - m.data_abertura).total_seconds() / 86400 for m in resolvidas]
        tempo_medio = round(sum(tempos) / len(tempos), 1)
    else:
        tempo_medio = 0

    # Custo por veículo
    veiculos_distintos = executadas.values('veiculo').distinct().count()
    custo_por_veiculo = float(valor_total_executado / veiculos_distintos) if veiculos_distintos > 0 else 0

    return {
        'total_os': total_os,
        'valor_total_executado': float(valor_total_executado),
        'valor_aprovado_executado': float(aprovado_executado),
        'ticket_medio': float(ticket_medio),
        'pct_prazo': pct_prazo,
        'tempo_medio_dias': tempo_medio,
        'total_executadas': total_executadas,
        'custo_por_veiculo': custo_por_veiculo,
    }


def _cache_key(prefixo, inicio, fim, unidade):
    i = inicio.isoformat() if inicio else 'todos'
    f = fim.isoformat() if fim else 'agora'
    u = unidade if unidade is not None else 'todas'
    return f'{prefixo}:{i}:{f}:{u}'


def calcular_kpis(inicio, fim, unidade=None):
    chave = _cache_key('kpis', inicio, fim, unidade)
    cached = cache.get(chave)
    if cached is not None:
        return cached

    kpis = _calcular_kpis_raw(inicio, fim, unidade)

    # Tendências (variação % vs período anterior)
    ant_inicio, ant_fim = _periodo_anterior(inicio, fim)
    if ant_inicio is not None:
        ant = _calcular_kpis_raw(ant_inicio, ant_fim, unidade)
        tendencias = {}
        for chave in ['total_os', 'valor_total_executado', 'valor_aprovado_executado',
                       'ticket_medio', 'pct_prazo', 'tempo_medio_dias', 'total_executadas',
                       'custo_por_veiculo']:
            atual = kpis[chave]
            anterior = ant[chave]
            if anterior and anterior != 0:
                tendencias[chave] = round((atual - anterior) / abs(anterior) * 100, 1)
            else:
                tendencias[chave] = None
        kpis['tendencias'] = tendencias
    else:
        kpis['tendencias'] = None

    cache.set(chave, kpis, CACHE_TIMEOUT)
    return kpis


def dados_graficos(inicio, fim, unidade=None):
    chave = _cache_key('graficos', inicio, fim, unidade)
    cached = cache.get(chave)
    if cached is not None:
        return cached

    qs = _filtrar_qs(Manutencao.objects, inicio, fim, unidade)

    # OS por Status
    os_por_status = dict(qs.values_list('status').annotate(c=Count('id')).order_by('-c'))

    # Evolução mensal
    from django.db.models.functions import TruncMonth
    evolucao = list(
        qs.annotate(mes=TruncMonth('data_abertura'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )
    evolucao_mensal = {
        'labels': [e['mes'].strftime('%b/%Y') for e in evolucao],
        'data': [e['total'] for e in evolucao],
    }

    # Top 10 veículos por gasto
    top_veiculos = list(
        qs.filter(status='Executada')
        .values('veiculo__placa')
        .annotate(total=Sum('valor_total'))
        .order_by('-total')[:10]
    )

    # Top 10 oficinas por volume
    orc_filter = {'manutencao__data_abertura__lte': fim}
    if inicio is not None:
        orc_filter['manutencao__data_abertura__gte'] = inicio
    if unidade is not None:
        orc_filter['manutencao__veiculo__unidade'] = unidade
    top_oficinas = list(
        Orcamento.objects.filter(**orc_filter)
        .values('oficina')
        .annotate(total=Count('id'))
        .order_by('-total')[:10]
    )

    # Distribuição Peças vs Serviços (exclui orçamentos recusados/cancelados)
    itens_filter = {
        'orcamento__manutencao__data_abertura__lte': fim,
        'orcamento__manutencao__status': 'Executada',
        'orcamento__status__in': ['Escolhido', 'Executado'],
    }
    if inicio is not None:
        itens_filter['orcamento__manutencao__data_abertura__gte'] = inicio
    if unidade is not None:
        itens_filter['orcamento__manutencao__veiculo__unidade'] = unidade
    itens_qs = ItemOrcamento.objects.filter(**itens_filter)
    dist_tipo = dict(itens_qs.values_list('tipo').annotate(t=Sum('total')))

    # OS por Setor
    os_por_setor = dict(
        qs.exclude(setor='')
        .values_list('setor')
        .annotate(c=Count('id'))
        .order_by('-c')
    )

    # --- Insights dinâmicos ---

    # Status
    if os_por_status:
        total = sum(os_por_status.values())
        top_status = next(iter(os_por_status))
        top_count = os_por_status[top_status]
        top_pct = round(top_count / total * 100) if total else 0
        status_insight = f"{top_status} concentra {top_pct}% das OS — {top_count} ordens"
    else:
        status_insight = ""

    # Evolução mensal
    if evolucao_mensal['data']:
        mes_pico = evolucao_mensal['labels'][evolucao_mensal['data'].index(max(evolucao_mensal['data']))]
        evolucao_insight = f"Pico de {max(evolucao_mensal['data'])} OS em {mes_pico}"
    else:
        evolucao_insight = ""

    # Top veículos
    if top_veiculos:
        top_v = top_veiculos[0]
        veiculos_insight = f"{top_v['veiculo__placa']} lidera com R$ {float(top_v['total']):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    else:
        veiculos_insight = ""

    # Top oficinas
    if top_oficinas:
        top_o = top_oficinas[0]
        oficinas_insight = f"{top_o['oficina'][:30]} lidera com {top_o['total']} orçamentos"
    else:
        oficinas_insight = ""

    # Peças vs Serviços
    dist_tipo_float = {k: float(v) for k, v in dist_tipo.items()}
    total_dist = sum(dist_tipo_float.values())
    if total_dist > 0:
        pca_val = dist_tipo_float.get('PCA', 0)
        srv_val = dist_tipo_float.get('SRV', 0)
        pca_pct = round(pca_val / total_dist * 100)
        tipo_insight = f"Peças representam {pca_pct}% do valor total" if pca_pct >= 50 else f"Serviços representam {100 - pca_pct}% do valor total"
    else:
        tipo_insight = ""

    # Setor
    if os_por_setor:
        total_setor = sum(os_por_setor.values())
        top_setor = next(iter(os_por_setor))
        top_setor_count = os_por_setor[top_setor]
        setor_pct = round(top_setor_count / total_setor * 100) if total_setor else 0
        setor_insight = f"{top_setor} concentra {setor_pct}% das OS — {top_setor_count} ordens"
    else:
        setor_insight = ""

    resultado = {
        'os_por_status': os_por_status,
        'status_insight': status_insight,
        'evolucao_mensal': evolucao_mensal,
        'evolucao_insight': evolucao_insight,
        'top_veiculos': [
            {'placa': v['veiculo__placa'], 'total': float(v['total'])}
            for v in top_veiculos
        ],
        'veiculos_insight': veiculos_insight,
        'top_oficinas': [
            {'oficina': o['oficina'][:40], 'total': o['total']}
            for o in top_oficinas
        ],
        'oficinas_insight': oficinas_insight,
        'dist_tipo': dist_tipo_float,
        'tipo_insight': tipo_insight,
        'os_por_setor': os_por_setor,
        'setor_insight': setor_insight,
    }

    cache.set(chave, resultado, CACHE_TIMEOUT)
    return resultado
