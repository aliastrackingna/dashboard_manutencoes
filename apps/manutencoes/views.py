import re
from collections import OrderedDict

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .models import Manutencao


def detalhe(request, numero_os):
    manutencao = get_object_or_404(Manutencao, numero_os=numero_os)
    orcamentos = manutencao.orcamentos.prefetch_related('itens').all()
    return render(request, 'manutencoes/detalhe.html', {
        'manutencao': manutencao,
        'orcamentos': orcamentos,
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
    todas_chaves = OrderedDict()
    for orc in orcamentos:
        for item in orc.itens.all():
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
