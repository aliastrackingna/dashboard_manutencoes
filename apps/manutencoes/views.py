import re
from collections import OrderedDict
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Max, Min, Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import ItemOrcamento, Manutencao, Orcamento

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
                todas_chaves[chave] = item.descricao

    # Montar linhas de comparação
    linhas = []
    for chave, descricao in todas_chaves.items():
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
        })

    linhas.sort(key=lambda l: l['descricao'])

    return render(request, 'manutencoes/comparar.html', {
        'manutencao': manutencao,
        'orcamentos': orcamentos,
        'linhas': linhas,
    })


def analise_precos(request, numero_os):
    manutencao = get_object_or_404(Manutencao, numero_os=numero_os)
    orcamentos = manutencao.orcamentos.prefetch_related('itens').all()

    # Agrupar itens por (descricao, tipo), priorizando orçamento vencedor
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
            chave = (item.descricao.upper().strip(), item.tipo)
            if chave not in itens_por_chave:
                itens_por_chave[chave] = item

    # Para cada item único, consultar histórico de outras OS
    analise = []
    for (descricao, tipo), item in itens_por_chave.items():
        historico = ItemOrcamento.objects.filter(
            descricao__iexact=descricao,
            tipo=tipo,
            orcamento__status__in=STATUSES_APROVADOS,
        ).exclude(
            orcamento__manutencao=manutencao,
        ).aggregate(
            ocorrencias=Count('id'),
            valor_min=Min('valor_unit'),
            valor_max=Max('valor_unit'),
            valor_medio=Avg('valor_unit'),
        )

        preco_atual = item.valor_unit
        ocorrencias = historico['ocorrencias']
        valor_medio = historico['valor_medio']

        if ocorrencias > 0 and valor_medio:
            variacao = ((preco_atual - Decimal(str(valor_medio))) / Decimal(str(valor_medio))) * 100
            if variacao > 10:
                classificacao = 'acima'
            elif variacao < -10:
                classificacao = 'abaixo'
            else:
                classificacao = 'dentro'
        else:
            variacao = None
            classificacao = 'sem_historico'

        analise.append({
            'item': item,
            'descricao': descricao,
            'tipo': tipo,
            'preco_atual': preco_atual,
            'ocorrencias': ocorrencias,
            'valor_min': historico['valor_min'],
            'valor_max': historico['valor_max'],
            'valor_medio': valor_medio,
            'variacao': variacao,
            'classificacao': classificacao,
        })

    # Ordenar: acima primeiro (maior variação no topo), depois dentro, abaixo, sem_historico
    ordem_class = {'acima': 0, 'dentro': 1, 'abaixo': 2, 'sem_historico': 3}
    analise.sort(key=lambda a: (ordem_class[a['classificacao']], -(a['variacao'] or 0)))

    total_itens = len(analise)
    itens_acima = sum(1 for a in analise if a['classificacao'] == 'acima')
    itens_sem_historico = sum(1 for a in analise if a['classificacao'] == 'sem_historico')

    return render(request, 'manutencoes/analise_precos.html', {
        'manutencao': manutencao,
        'analise': analise,
        'total_itens': total_itens,
        'itens_acima': itens_acima,
        'itens_sem_historico': itens_sem_historico,
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
