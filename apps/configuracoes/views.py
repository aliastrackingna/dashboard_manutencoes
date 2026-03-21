from decimal import Decimal, InvalidOperation
from io import StringIO

from django.core.management import call_command
from django.shortcuts import render, redirect
from django.contrib import messages

from apps.auditoria.models import LogAuditoria
from .models import ConfigGeral, KPIConfig


DEFAULT_KPIS = [
    {'chave': 'custo_maximo_os', 'descricao': 'Custo máximo aceitável por OS', 'valor': 5000, 'unidade': 'R$'},
    {'chave': 'sla_dias_execucao', 'descricao': 'SLA de dias para execução', 'valor': 15, 'unidade': 'dias'},
    {'chave': 'meta_prazo_pct', 'descricao': 'Meta de OS dentro do prazo', 'valor': 80, 'unidade': '%'},
    {'chave': 'ticket_medio_alerta', 'descricao': 'Ticket médio para alerta', 'valor': 3000, 'unidade': 'R$'},
]


def kpis(request):
    # Ensure defaults exist
    for kpi in DEFAULT_KPIS:
        KPIConfig.objects.get_or_create(
            chave=kpi['chave'],
            defaults=kpi,
        )

    email_backup_obj, _ = ConfigGeral.objects.get_or_create(
        chave='email_backup',
        defaults={'descricao': 'E-mail destinatário do backup Excel diário', 'valor': ''},
    )

    if request.method == 'POST':
        # KPIs
        alteracoes = []
        for kpi in KPIConfig.objects.all():
            novo_valor = request.POST.get(f'valor_{kpi.id}')
            if novo_valor is not None:
                try:
                    valor_anterior = kpi.valor
                    kpi.valor = Decimal(novo_valor.replace(',', '.'))
                    if kpi.valor != valor_anterior:
                        alteracoes.append(
                            f'{kpi.descricao} alterado de {valor_anterior} {kpi.unidade}'
                            f' para {kpi.valor} {kpi.unidade}'
                        )
                    kpi.save()
                except (InvalidOperation, ValueError):
                    messages.error(request, f'Valor inválido para "{kpi.descricao}".')
        for desc in alteracoes:
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo='ALTERACAO',
                descricao=desc,
            )

        # E-mail backup
        novo_email = request.POST.get('email_backup', '').strip()
        if novo_email != email_backup_obj.valor:
            valor_anterior = email_backup_obj.valor
            email_backup_obj.valor = novo_email
            email_backup_obj.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo='ALTERACAO',
                descricao=f'E-mail de backup alterado de "{valor_anterior}" para "{novo_email}"',
            )

        messages.success(request, 'Configurações atualizadas.')
        return redirect('configuracoes:kpis')

    kpis_list = KPIConfig.objects.all().order_by('chave')
    return render(request, 'configuracoes/kpis.html', {
        'kpis': kpis_list,
        'email_backup': email_backup_obj.valor,
    })


def enviar_backup(request):
    if request.method == 'POST':
        stdout = StringIO()
        stderr = StringIO()
        try:
            call_command('backup_excel', stdout=stdout, stderr=stderr)
            erro = stderr.getvalue()
            if erro:
                messages.error(request, erro.strip())
            else:
                messages.success(request, stdout.getvalue().strip())
                LogAuditoria.objects.create(
                    usuario=request.user,
                    tipo='ALTERACAO',
                    descricao='Backup Excel enviado manualmente',
                )
        except Exception as e:
            messages.error(request, f'Erro ao enviar backup: {e}')
    return redirect('configuracoes:kpis')
