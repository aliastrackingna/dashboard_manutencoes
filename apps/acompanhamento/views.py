from datetime import date

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.auditoria.models import LogAuditoria
from apps.manutencoes.models import Manutencao

from .forms import AcompanhamentoForm
from .models import Acompanhamento


def lista(request):
    qs = (
        Acompanhamento.objects
        .filter(usuario=request.user)
        .select_related('manutencao', 'manutencao__veiculo')
    )

    somente_ativas = request.GET.get('somente_ativas', '1')
    if somente_ativas == '1':
        qs = qs.filter(finalizado=False)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(manutencao__numero_os__icontains=q)
            | Q(manutencao__veiculo__placa__icontains=q)
        )

    total_ativas = Acompanhamento.objects.filter(usuario=request.user, finalizado=False).count()
    total_vencidas = Acompanhamento.objects.filter(
        usuario=request.user, finalizado=False, data_limite__lt=date.today()
    ).count()
    total_finalizadas = Acompanhamento.objects.filter(usuario=request.user, finalizado=True).count()

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'acompanhamento/lista.html', {
        'page': page,
        'q': q,
        'somente_ativas': somente_ativas,
        'total_ativas': total_ativas,
        'total_vencidas': total_vencidas,
        'total_finalizadas': total_finalizadas,
    })


@require_POST
def toggle(request, numero_os):
    manutencao = get_object_or_404(Manutencao, numero_os=numero_os)
    acomp = Acompanhamento.objects.filter(usuario=request.user, manutencao=manutencao).first()

    if acomp:
        acomp.delete()
        LogAuditoria.objects.create(
            usuario=request.user,
            tipo='ALTERACAO',
            descricao=f'Removeu acompanhamento da OS {numero_os}',
        )
        messages.success(request, f'Acompanhamento da OS {numero_os} removido.')
        return redirect('manutencoes:detalhe', numero_os=numero_os)
    else:
        acomp = Acompanhamento.objects.create(
            usuario=request.user,
            manutencao=manutencao,
        )
        LogAuditoria.objects.create(
            usuario=request.user,
            tipo='ADICAO',
            descricao=f'Adicionou acompanhamento da OS {numero_os}',
        )
        messages.success(request, f'OS {numero_os} adicionada ao acompanhamento.')
        return redirect('acompanhamento:editar', pk=acomp.pk)


def editar(request, pk):
    acomp = get_object_or_404(Acompanhamento, pk=pk, usuario=request.user)

    if request.method == 'POST':
        form = AcompanhamentoForm(request.POST, instance=acomp)
        if form.is_valid():
            obj = form.save(commit=False)
            if obj.finalizado and not acomp.finalizado_em:
                obj.finalizado_em = timezone.now()
            elif not obj.finalizado:
                obj.finalizado_em = None
            obj.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo='ALTERACAO',
                descricao=f'Editou acompanhamento da OS {acomp.manutencao_id}',
            )
            messages.success(request, 'Acompanhamento atualizado.')
            return redirect('acompanhamento:lista')
    else:
        form = AcompanhamentoForm(instance=acomp)

    return render(request, 'acompanhamento/editar.html', {
        'form': form,
        'acomp': acomp,
    })
