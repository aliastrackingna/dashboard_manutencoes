from django.shortcuts import render, get_object_or_404
from .models import Manutencao


def detalhe(request, numero_os):
    manutencao = get_object_or_404(Manutencao, numero_os=numero_os)
    orcamentos = manutencao.orcamentos.prefetch_related('itens').all()
    return render(request, 'manutencoes/detalhe.html', {
        'manutencao': manutencao,
        'orcamentos': orcamentos,
    })
