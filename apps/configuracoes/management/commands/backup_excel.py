import os
import tempfile
from datetime import datetime

import pandas as pd
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand

from apps.auditoria.models import LogAuditoria
from apps.configuracoes.models import ConfigGeral, KPIConfig
from apps.importacao.models import RegistroImportacao
from apps.manutencoes.models import ItemOrcamento, Manutencao, Orcamento
from apps.multas.models import Multa
from apps.veiculos.models import Veiculo


WORKSHEETS = [
    ('Veículos', Veiculo),
    ('Manutenções', Manutencao),
    ('Orçamentos', Orcamento),
    ('Itens Orçamento', ItemOrcamento),
    ('Multas', Multa),
    ('Config KPI', KPIConfig),
    ('Config Geral', ConfigGeral),
    ('Importações', RegistroImportacao),
    ('Auditoria', LogAuditoria),
]


class Command(BaseCommand):
    help = 'Exporta todos os dados para Excel e envia por e-mail'

    def handle(self, *args, **options):
        # Ler e-mail destinatário
        try:
            email_dest = ConfigGeral.objects.get(chave='email_backup').valor
        except ConfigGeral.DoesNotExist:
            email_dest = ''

        if not email_dest:
            self.stderr.write(self.style.ERROR(
                'E-mail destinatário não configurado. '
                'Defina em Configurações > E-mail para backup.'
            ))
            return

        data_str = datetime.now().strftime('%Y-%m-%d')
        nome_arquivo = f'backup_frota_{data_str}.xlsx'
        caminho = os.path.join(tempfile.gettempdir(), nome_arquivo)

        try:
            self._gerar_excel(caminho)
            self._enviar_email(email_dest, caminho, nome_arquivo, data_str)
            self.stdout.write(self.style.SUCCESS(
                f'Backup enviado para {email_dest} ({nome_arquivo})'
            ))
        finally:
            if os.path.exists(caminho):
                os.remove(caminho)

    def _gerar_excel(self, caminho):
        with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
            # Models Django
            for nome_aba, model in WORKSHEETS:
                qs = model.objects.all()
                if qs.exists():
                    campos = [f.name for f in model._meta.get_fields()
                              if hasattr(f, 'column') or hasattr(f, 'attname')]
                    dados = list(qs.values(*campos))
                else:
                    campos = [f.name for f in model._meta.get_fields()
                              if hasattr(f, 'column') or hasattr(f, 'attname')]
                    dados = []
                df = pd.DataFrame(dados, columns=campos)
                self._remover_timezone(df)
                df.to_excel(writer, sheet_name=nome_aba, index=False)

    @staticmethod
    def _remover_timezone(df):
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.tz_localize(None)

    def _enviar_email(self, destinatario, caminho, nome_arquivo, data_str):
        remetente = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        if not remetente:
            raise RuntimeError(
                'Remetente não configurado. Defina EMAIL_HOST_USER ou DEFAULT_FROM_EMAIL.'
            )
        email = EmailMessage(
            subject=f'Backup Frota — {data_str}',
            body=(
                f'Segue em anexo o backup completo do sistema Manutenção Frota '
                f'gerado em {data_str}.'
            ),
            from_email=remetente,
            to=[destinatario],
        )
        email.attach_file(caminho)
        email.send()
