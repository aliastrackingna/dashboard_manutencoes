from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Multa
from .forms import MultaEditForm

OPCOES_POR_PAGINA = [15, 20, 30, 50, 100]


def lista(request):
    qs = Multa.objects.select_related('veiculo').all()

    placa = request.GET.get('placa', '').strip()
    if placa:
        qs = qs.filter(veiculo__placa=placa)

    unidade = request.GET.get('unidade', '').strip()
    if unidade:
        qs = qs.filter(veiculo__unidade=unidade)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(veiculo__placa__icontains=q)
            | Q(veiculo__modelo__icontains=q)
            | Q(descricao_infracao__icontains=q)
        )

    por_pagina = request.GET.get('por_pagina', '20')
    try:
        por_pagina_int = int(por_pagina)
        if por_pagina_int not in OPCOES_POR_PAGINA:
            por_pagina_int = 20
    except ValueError:
        por_pagina_int = 20

    paginator = Paginator(qs, por_pagina_int)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'multas/lista.html', {
        'page': page,
        'q': q,
        'placa': placa,
        'unidade': unidade,
        'por_pagina': str(por_pagina_int),
        'opcoes_por_pagina': OPCOES_POR_PAGINA,
    })


def editar(request, auto_infracao):
    multa = get_object_or_404(Multa, auto_infracao=auto_infracao)

    if request.method == 'POST':
        form = MultaEditForm(request.POST, instance=multa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Multa atualizada com sucesso.')
            return redirect('multas:lista')
    else:
        form = MultaEditForm(instance=multa)

    return render(request, 'multas/editar.html', {
        'form': form,
        'multa': multa,
    })
