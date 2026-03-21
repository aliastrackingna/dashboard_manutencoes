from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator

from apps.auditoria.models import LogAuditoria
from .models import Veiculo
from .forms import VeiculoForm


def lista(request):
    qs = Veiculo.objects.all()

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(placa__icontains=q) | qs.filter(marca__icontains=q) | qs.filter(modelo__icontains=q)

    ativo = request.GET.get('ativo')
    if ativo == '1':
        qs = qs.filter(ativo=True)
    elif ativo == '0':
        qs = qs.filter(ativo=False)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'veiculos/lista.html', {
        'page': page,
        'q': q,
        'ativo': ativo,
    })


def criar(request):
    if request.method == 'POST':
        form = VeiculoForm(request.POST)
        if form.is_valid():
            veiculo = form.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo='ADICAO',
                descricao=f'Veículo {veiculo.placa} criado ({veiculo.marca} {veiculo.modelo})',
            )
            messages.success(request, 'Veículo criado com sucesso.')
            return redirect('veiculos:lista')
    else:
        form = VeiculoForm()
    return render(request, 'veiculos/form.html', {'form': form, 'titulo': 'Novo Veículo'})


def editar(request, placa):
    veiculo = get_object_or_404(Veiculo, placa=placa)
    if request.method == 'POST':
        ativo_anterior = veiculo.ativo
        form = VeiculoForm(request.POST, instance=veiculo)
        if form.is_valid():
            form.save()
            alteracoes = []
            if form.cleaned_data['ativo'] != ativo_anterior:
                estado = 'ativado' if form.cleaned_data['ativo'] else 'desativado'
                alteracoes.append(f'Veículo {veiculo.placa} {estado}')
            changed = form.changed_data
            campos_rastreados = [f for f in changed if f != 'ativo']
            if campos_rastreados:
                alteracoes.append(
                    f'Veículo {veiculo.placa} editado ({", ".join(campos_rastreados)})'
                )
            for desc in alteracoes:
                LogAuditoria.objects.create(
                    usuario=request.user,
                    tipo='ALTERACAO',
                    descricao=desc,
                )
            messages.success(request, 'Veículo atualizado com sucesso.')
            return redirect('veiculos:detalhe', placa=veiculo.placa)
    else:
        form = VeiculoForm(instance=veiculo)
    return render(request, 'veiculos/form.html', {'form': form, 'titulo': 'Editar Veículo', 'veiculo': veiculo})


def detalhe(request, placa):
    veiculo = get_object_or_404(Veiculo, placa=placa)
    manutencoes = veiculo.manutencoes.all()[:50]
    return render(request, 'veiculos/detalhe.html', {
        'veiculo': veiculo,
        'manutencoes': manutencoes,
    })


def autocomplete(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    veiculos = Veiculo.objects.filter(placa__icontains=q, ativo=True)[:10]
    return JsonResponse([
        {'placa': v.placa, 'label': f'{v.placa} — {v.marca} {v.modelo}'}
        for v in veiculos
    ], safe=False)
