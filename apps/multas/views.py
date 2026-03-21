from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from apps.auditoria.models import LogAuditoria
from .models import Multa
from .forms import MultaEditForm, MultaForm

OPCOES_POR_PAGINA = [15, 20, 30, 50, 100]


def lista(request):
    qs = Multa.objects.select_related('veiculo').all()

    placa = request.GET.get('placa', '').strip()
    if placa:
        qs = qs.filter(veiculo__placa=placa)

    unidade = request.GET.get('unidade', '').strip()
    if unidade:
        qs = qs.filter(veiculo__unidade=unidade)

    situacao = request.GET.get('situacao', '').strip()
    if situacao:
        qs = qs.filter(situacao=situacao)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(auto_infracao__icontains=q)
            | Q(veiculo__placa__icontains=q)
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
        'situacao': situacao,
        'situacao_choices': Multa.SITUACAO_CHOICES,
        'por_pagina': str(por_pagina_int),
        'opcoes_por_pagina': OPCOES_POR_PAGINA,
    })


def criar(request):
    if request.method == 'POST':
        form = MultaForm(request.POST)
        if form.is_valid():
            multa = form.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo='ADICAO',
                descricao=f'Multa {multa.auto_infracao} adicionada para o veículo {multa.veiculo_id}',
            )
            messages.success(request, 'Multa cadastrada com sucesso.')
            return redirect('multas:lista')
    else:
        form = MultaForm()
    return render(request, 'multas/criar.html', {'form': form})


def editar(request, auto_infracao):
    multa = get_object_or_404(Multa, auto_infracao=auto_infracao)

    if request.method == 'POST':
        situacao_anterior = multa.situacao
        protocolo_anterior = multa.protocolo_sei
        observacao_anterior = multa.observacao
        form = MultaEditForm(request.POST, instance=multa)
        if form.is_valid():
            form.save()
            alteracoes = []
            if form.cleaned_data['situacao'] != situacao_anterior:
                alteracoes.append(
                    f'Multa {multa.auto_infracao} do veículo {multa.veiculo_id}'
                    f' alterada para {form.cleaned_data["situacao"]}'
                )
            if form.cleaned_data.get('protocolo_sei', '') != protocolo_anterior:
                alteracoes.append(
                    f'Protocolo SEI da multa {multa.auto_infracao} do veículo {multa.veiculo_id}'
                    f' alterado para "{form.cleaned_data["protocolo_sei"]}"'
                )
            if form.cleaned_data.get('observacao', '') != observacao_anterior:
                alteracoes.append(
                    f'Observação da multa {multa.auto_infracao} do veículo {multa.veiculo_id} alterada'
                )
            for desc in alteracoes:
                LogAuditoria.objects.create(
                    usuario=request.user,
                    tipo='ALTERACAO',
                    descricao=desc,
                )
            messages.success(request, 'Multa atualizada com sucesso.')
            return redirect('multas:lista')
    else:
        form = MultaEditForm(instance=multa)

    return render(request, 'multas/editar.html', {
        'form': form,
        'multa': multa,
    })
