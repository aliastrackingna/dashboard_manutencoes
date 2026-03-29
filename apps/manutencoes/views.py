import re
from collections import OrderedDict
from datetime import timedelta
from decimal import Decimal
from math import ceil, floor

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Max, Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import ItemOrcamento, Manutencao, Orcamento
from .normalizacao import construir_chave_item_canonica

STATUSES_APROVADOS = ['Escolhido', 'Executado', 'Em Execução']

OPCOES_POR_PAGINA = [20, 30, 50, 100]

STATUS_CHOICES = [
    'Aberta',
    'Autorizada Execução',
    'Cancelada pelo Usuário',
    'Em Execução',
    'Executada',
    'Orçamentação',
]


def _normalizar_texto(valor):
    return re.sub(r'\s+', ' ', (valor or '').strip().upper())


def _assinaturas_item(item):
    assinaturas = []
    codigo = _normalizar_texto(item.codigo_item)
    if codigo:
        assinaturas.append(('codigo', codigo))

    descricao = _normalizar_texto(item.descricao)
    if descricao:
        assinaturas.append(('descricao', descricao))

    return assinaturas


def _montar_historico_itens(manutencao, janela_meses):
    referencia = manutencao.data_abertura or timezone.now()
    limite = referencia - timedelta(days=janela_meses * 30)

    historico_qs = ItemOrcamento.objects.filter(
        orcamento__manutencao__veiculo=manutencao.veiculo,
        orcamento__manutencao__status='Executada',
        orcamento__status__in=STATUSES_APROVADOS,
    ).exclude(
        orcamento__manutencao=manutencao,
    )

    if manutencao.data_abertura:
        historico_qs = historico_qs.filter(
            orcamento__manutencao__data_abertura__lt=manutencao.data_abertura,
        )

    historico_qs = historico_qs.select_related(
        'orcamento',
        'orcamento__manutencao',
    ).order_by(
        '-orcamento__manutencao__data_abertura',
        '-orcamento__id',
    )

    por_assinatura = {}
    for item in historico_qs:
        assinaturas = _assinaturas_item(item)
        if not assinaturas:
            continue

        manutencao_hist = item.orcamento.manutencao
        data_hist = manutencao_hist.data_encerramento or manutencao_hist.data_abertura
        if not data_hist:
            continue

        dias_desde = max((referencia.date() - data_hist.date()).days, 0)
        meses_desde = round(dias_desde / 30, 1)

        payload = {
            'numero_os': manutencao_hist.numero_os,
            'oficina': item.orcamento.oficina,
            'data': data_hist,
            'valor_unit': item.valor_unit,
            'total': item.total,
            'meses_desde': meses_desde,
            'dias_desde': dias_desde,
            'alerta_repeticao': data_hist >= limite,
        }

        for assinatura in assinaturas:
            if assinatura not in por_assinatura:
                por_assinatura[assinatura] = payload

    return por_assinatura


def _buscar_historico_item(historico_por_assinatura, assinaturas):
    for assinatura in assinaturas:
        historico = historico_por_assinatura.get(assinatura)
        if historico:
            return historico
    return None


def _chave_canonica_item(item):
    if item.chave_item_canonica:
        return item.chave_item_canonica
    normalizado = construir_chave_item_canonica(item.tipo, item.codigo_item, item.descricao)
    return normalizado['chave_item_canonica']


def _percentil_decimal(valores_ordenados, percentual):
    if not valores_ordenados:
        return None

    posicao = (len(valores_ordenados) - 1) * percentual
    inferior = floor(posicao)
    superior = ceil(posicao)

    if inferior == superior:
        return valores_ordenados[inferior]

    peso_superior = Decimal(str(posicao - inferior))
    peso_inferior = Decimal('1') - peso_superior
    return (valores_ordenados[inferior] * peso_inferior) + (valores_ordenados[superior] * peso_superior)


def _mediana_decimal(valores):
    ordenados = sorted(valores)
    return _percentil_decimal(ordenados, 0.5)


def lista(request):
    qs = Manutencao.objects.select_related('veiculo').all()

    q = request.GET.get('q', '').strip()
    if q:
        if q.isdigit():
            qs = qs.filter(numero_os__regex=r'- ' + q + r'$')
        else:
            qs = qs.filter(
                Q(numero_os__icontains=q)
                | Q(veiculo__placa__icontains=q)
                | Q(modelo_veiculo__icontains=q)
                | Q(descricao__icontains=q)
            )

    status = request.GET.get('status', '').strip()
    if status:
        qs = qs.filter(status=status)

    placa = request.GET.get('placa', '').strip()
    if placa:
        qs = qs.filter(veiculo__placa=placa)

    unidade = request.GET.get('unidade', '').strip()
    if unidade:
        qs = qs.filter(veiculo__unidade=unidade)

    oficina = request.GET.get('oficina', '').strip()
    if oficina:
        qs = qs.filter(orcamentos__oficina=oficina).distinct()

    por_pagina = request.GET.get('por_pagina', '20')
    try:
        por_pagina_int = int(por_pagina)
        if por_pagina_int not in OPCOES_POR_PAGINA:
            por_pagina_int = 20
    except ValueError:
        por_pagina_int = 20

    paginator = Paginator(qs, por_pagina_int)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'manutencoes/lista.html', {
        'page': page,
        'q': q,
        'status': status,
        'placa': placa,
        'unidade': unidade,
        'oficina': oficina,
        'por_pagina': str(por_pagina_int),
        'opcoes_por_pagina': OPCOES_POR_PAGINA,
        'status_choices': STATUS_CHOICES,
    })


def detalhe(request, numero_os):
    manutencao = get_object_or_404(Manutencao, numero_os=numero_os)
    orcamentos = manutencao.orcamentos.prefetch_related('itens').all()
    acompanhando = manutencao.acompanhamentos.filter(usuario=request.user).exists()
    return render(request, 'manutencoes/detalhe.html', {
        'manutencao': manutencao,
        'orcamentos': orcamentos,
        'acompanhando': acompanhando,
    })


def comparar_orcamentos(request, numero_os):
    manutencao = get_object_or_404(Manutencao, numero_os=numero_os)
    orcamentos = list(manutencao.orcamentos.prefetch_related('itens').all())
    comparar_historico = True
    janela_meses = 24

    if len(orcamentos) < 2:
        messages.warning(request, 'É necessário pelo menos 2 orçamentos para comparar.')
        return redirect('manutencoes:detalhe', numero_os=numero_os)

    for orc in orcamentos:
        orc.oficina_curta = re.split(r'[-=]', orc.oficina)[0].strip() if orc.oficina else ''

    # Coletar todos os itens únicos (chave = codigo_item ou descricao)
    # Itens com valor zerado são ignorados na comparação
    todas_chaves = OrderedDict()
    for orc in orcamentos:
        for item in orc.itens.all():
            if item.total == 0:
                continue
            chave = item.codigo_item if item.codigo_item else item.descricao
            if chave not in todas_chaves:
                todas_chaves[chave] = {
                    'descricao': item.descricao,
                    'assinaturas': _assinaturas_item(item),
                }

    historico_por_assinatura = {}
    if comparar_historico:
        historico_por_assinatura = _montar_historico_itens(manutencao, janela_meses)

    # Montar linhas de comparação
    linhas = []
    for chave, dados_item in todas_chaves.items():
        descricao = dados_item['descricao']
        valores = {}
        for orc in orcamentos:
            item_encontrado = None
            for item in orc.itens.all():
                if item.total == 0:
                    continue
                item_chave = item.codigo_item if item.codigo_item else item.descricao
                if item_chave == chave:
                    item_encontrado = item
                    break
            valores[orc.codigo_orcamento] = item_encontrado

        # Determinar se é exclusivo e min/max
        valores_presentes = {k: v.total for k, v in valores.items() if v is not None}
        exclusivo = len(valores_presentes) == 1
        menor_valor = min(valores_presentes.values()) if valores_presentes else None
        maior_valor = max(valores_presentes.values()) if valores_presentes else None
        tem_diferenca = menor_valor != maior_valor

        celulas = []
        for orc in orcamentos:
            item = valores[orc.codigo_orcamento]
            if item is None:
                celulas.append({'item': None, 'classe': '', 'exclusivo': False})
            elif exclusivo:
                celulas.append({'item': item, 'classe': 'exclusivo', 'exclusivo': True})
            elif tem_diferenca and item.total == menor_valor:
                celulas.append({'item': item, 'classe': 'menor', 'exclusivo': False})
            elif tem_diferenca and item.total == maior_valor:
                celulas.append({'item': item, 'classe': 'maior', 'exclusivo': False})
            else:
                celulas.append({'item': item, 'classe': '', 'exclusivo': False})

        linhas.append({
            'chave': chave,
            'descricao': descricao.upper(),
            'celulas': celulas,
            'exclusivo': exclusivo,
            'historico': _buscar_historico_item(
                historico_por_assinatura,
                dados_item['assinaturas'],
            ),
        })

    linhas.sort(key=lambda l: l['descricao'])

    return render(request, 'manutencoes/comparar.html', {
        'manutencao': manutencao,
        'orcamentos': orcamentos,
        'linhas': linhas,
        'comparar_historico': comparar_historico,
        'janela_meses': janela_meses,
    })


def analise_precos(request, numero_os):
    manutencao = get_object_or_404(Manutencao, numero_os=numero_os)
    orcamentos = manutencao.orcamentos.prefetch_related('itens').all()

    # Agrupar itens por chave canônica, priorizando orçamento vencedor
    itens_por_chave = OrderedDict()
    # Primeiro passa pelos orçamentos aprovados, depois os demais
    orcamentos_ordenados = sorted(
        orcamentos,
        key=lambda o: (0 if o.status in STATUSES_APROVADOS else 1, o.valor),
    )
    for orc in orcamentos_ordenados:
        for item in orc.itens.all():
            if item.total == 0:
                continue
            chave = _chave_canonica_item(item)
            if chave not in itens_por_chave:
                itens_por_chave[chave] = item

    # Para cada item único, consultar histórico de outras OS
    analise = []
    for chave_canonica, item in itens_por_chave.items():
        historico_qs = ItemOrcamento.objects.filter(
            orcamento__status__in=STATUSES_APROVADOS,
        ).exclude(
            orcamento__manutencao=manutencao,
        )

        if chave_canonica:
            historico_qs = historico_qs.filter(chave_item_canonica=chave_canonica)
        else:
            historico_qs = historico_qs.filter(
                descricao__iexact=item.descricao,
                tipo=item.tipo,
            )

        historico = historico_qs.aggregate(
            ocorrencias=Count('id'),
            valor_min=Min('valor_unit'),
            valor_max=Max('valor_unit'),
            valor_medio=Avg('valor_unit'),
        )

        valores_historicos = list(historico_qs.values_list('valor_unit', flat=True))
        valores_historicos_ordenados = sorted(valores_historicos)
        mediana = _mediana_decimal(valores_historicos_ordenados)
        q1 = _percentil_decimal(valores_historicos_ordenados, 0.25)
        q3 = _percentil_decimal(valores_historicos_ordenados, 0.75)
        dispersao_iqr = (q3 - q1) if q1 is not None and q3 is not None else None

        if mediana and mediana != 0 and dispersao_iqr is not None:
            dispersao_pct = (dispersao_iqr / mediana) * 100
        else:
            dispersao_pct = None

        preco_atual = item.valor_unit
        ocorrencias = historico['ocorrencias']
        valor_medio = historico['valor_medio']
        referencia_variacao = mediana if mediana is not None else valor_medio

        if ocorrencias > 0 and referencia_variacao:
            referencia_decimal = Decimal(str(referencia_variacao))
            variacao = ((preco_atual - referencia_decimal) / referencia_decimal) * 100
            if variacao > 10:
                classificacao = 'acima'
            elif variacao < -10:
                classificacao = 'abaixo'
            else:
                classificacao = 'dentro'
        else:
            variacao = None
            classificacao = 'sem_historico'

        if ocorrencias == 0 or mediana is None:
            alerta = 'sem_historico'
        elif mediana == 0:
            alerta = 'sem_historico'
        else:
            variacao_mediana = ((preco_atual - mediana) / mediana) * 100
            if dispersao_iqr is not None and ocorrencias >= 4:
                limite_medio = mediana + dispersao_iqr
                limite_alto = mediana + (dispersao_iqr * Decimal('2'))
                if preco_atual >= limite_alto:
                    alerta = 'alto'
                elif preco_atual >= limite_medio:
                    alerta = 'medio'
                else:
                    alerta = 'baixo'
            else:
                if variacao_mediana > 25:
                    alerta = 'alto'
                elif variacao_mediana > 10:
                    alerta = 'medio'
                else:
                    alerta = 'baixo'

        analise.append({
            'item': item,
            'descricao': item.descricao.upper().strip(),
            'tipo': item.tipo,
            'preco_atual': preco_atual,
            'ocorrencias': ocorrencias,
            'valor_min': historico['valor_min'],
            'valor_max': historico['valor_max'],
            'valor_medio': valor_medio,
            'valor_mediana': mediana,
            'q1': q1,
            'q3': q3,
            'dispersao_iqr': dispersao_iqr,
            'dispersao_pct': dispersao_pct,
            'variacao': variacao,
            'classificacao': classificacao,
            'alerta': alerta,
            'chave_item_canonica': chave_canonica,
        })

    # Ordenar: alerta alto primeiro, depois classificação e variação
    ordem_alerta = {'alto': 0, 'medio': 1, 'baixo': 2, 'sem_historico': 3}
    ordem_class = {'acima': 0, 'dentro': 1, 'abaixo': 2, 'sem_historico': 3}
    analise.sort(key=lambda a: (ordem_alerta[a['alerta']], ordem_class[a['classificacao']], -(a['variacao'] or 0)))

    total_itens = len(analise)
    itens_acima = sum(1 for a in analise if a['classificacao'] == 'acima')
    itens_sem_historico = sum(1 for a in analise if a['classificacao'] == 'sem_historico')
    itens_alerta_alto = sum(1 for a in analise if a['alerta'] == 'alto')
    itens_alerta_medio = sum(1 for a in analise if a['alerta'] == 'medio')

    return render(request, 'manutencoes/analise_precos.html', {
        'manutencao': manutencao,
        'analise': analise,
        'total_itens': total_itens,
        'itens_acima': itens_acima,
        'itens_sem_historico': itens_sem_historico,
        'itens_alerta_alto': itens_alerta_alto,
        'itens_alerta_medio': itens_alerta_medio,
    })


def oficinas(request):
    q = request.GET.get('q', '').strip()

    qs = (
        Orcamento.objects
        .values('oficina')
        .annotate(
            total_orcamentos=Count('id'),
            lancado=Count('id', filter=Q(status='Lançado')),
            escolhido=Count('id', filter=Q(status='Escolhido')),
            em_execucao=Count('id', filter=Q(status='Em Execução')),
            executado=Count('id', filter=Q(status='Executado')),
            recusado=Count('id', filter=Q(status='Recusado')),
            cancelado=Count('id', filter=Q(status='Cancelado')),
        )
        .order_by('oficina')
    )

    if q:
        qs = qs.filter(oficina__icontains=q)

    oficinas_list = list(qs)

    return render(request, 'manutencoes/oficinas.html', {
        'oficinas': oficinas_list,
        'q': q,
        'total': len(oficinas_list),
    })


def oficina_detalhe(request, nome):
    orcamentos_qs = (
        Orcamento.objects
        .filter(oficina=nome)
        .select_related('manutencao', 'manutencao__veiculo')
        .order_by('-data')
    )

    q = request.GET.get('q', '').strip()
    if q:
        orcamentos_qs = orcamentos_qs.filter(
            Q(manutencao__numero_os__icontains=q)
            | Q(manutencao__veiculo__placa__icontains=q)
        )

    por_pagina = request.GET.get('por_pagina', '25')
    try:
        por_pagina_int = int(por_pagina)
        if por_pagina_int not in [15, 25, 50, 100]:
            por_pagina_int = 25
    except ValueError:
        por_pagina_int = 25

    paginator = Paginator(orcamentos_qs, por_pagina_int)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'manutencoes/oficina_detalhe.html', {
        'nome_oficina': nome,
        'page': page,
        'q': q,
        'por_pagina': str(por_pagina_int),
        'opcoes_por_pagina': [15, 25, 50, 100],
    })
