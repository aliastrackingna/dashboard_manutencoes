import pandas as pd
from django.utils import timezone
from apps.veiculos.models import Veiculo
from apps.manutencoes.models import Manutencao
from .base import parse_decimal_br, parse_datetime_br, parse_bool_flag


def importar_manutencoes(file):
    df = pd.read_csv(
        file,
        sep=';',
        header=None,
        encoding='utf-8',
        dtype=str,
        quotechar='"',
    ).fillna('')

    inseridos = 0
    atualizados = 0
    erros = []

    for idx, row in df.iterrows():
        tipo = str(row.iloc[3]).strip() if len(row) > 3 else ''
        numero_os = str(row.iloc[4]).strip() if len(row) > 4 else ''
        empresa = str(row.iloc[5]).strip() if len(row) > 5 else ''
        setor = str(row.iloc[6]).strip() if len(row) > 6 else ''
        placa = str(row.iloc[7]).strip() if len(row) > 7 else ''
        modelo_veiculo = str(row.iloc[9]).strip() if len(row) > 9 else ''
        data_abertura_str = str(row.iloc[10]).strip() if len(row) > 10 else ''
        data_encerramento_str = str(row.iloc[11]).strip() if len(row) > 11 else ''
        data_integracao_str = str(row.iloc[12]).strip() if len(row) > 12 else ''
        data_cancelamento_str = str(row.iloc[13]).strip() if len(row) > 13 else ''
        descricao = str(row.iloc[14]).strip() if len(row) > 14 else ''
        status = str(row.iloc[15]).strip() if len(row) > 15 else ''
        flag_str = str(row.iloc[16]).strip() if len(row) > 16 else ''
        valor_pecas_str = str(row.iloc[17]).strip() if len(row) > 17 else ''
        valor_servicos_str = str(row.iloc[18]).strip() if len(row) > 18 else ''
        valor_total_str = str(row.iloc[19]).strip() if len(row) > 19 else ''

        if not numero_os:
            erros.append({
                'linha': idx + 1,
                'tipo': 'CAMPO_OBRIGATORIO',
                'motivo': 'numero_os vazio',
            })
            continue

        if not placa:
            erros.append({
                'linha': idx + 1,
                'tipo': 'CAMPO_OBRIGATORIO',
                'motivo': f"Placa vazia para OS '{numero_os}'",
            })
            continue

        if not Veiculo.objects.filter(placa=placa).exists():
            Veiculo.objects.create(
                placa=placa,
                marca='',
                modelo=modelo_veiculo,
            )

        data_abertura = parse_datetime_br(data_abertura_str)
        if not data_abertura:
            erros.append({
                'linha': idx + 1,
                'tipo': 'DATA_INVALIDA',
                'motivo': f"data_abertura inválida para OS '{numero_os}': '{data_abertura_str}'",
            })
            continue

        data_abertura = timezone.make_aware(data_abertura)
        data_encerramento = parse_datetime_br(data_encerramento_str)
        if data_encerramento:
            data_encerramento = timezone.make_aware(data_encerramento)

        data_integracao = parse_datetime_br(data_integracao_str)
        if data_integracao:
            data_integracao = timezone.make_aware(data_integracao)

        if status in ('Integrada Financeiro', 'XPTO'):
            status = 'Executada'

        defaults = {
            'tipo': tipo,
            'empresa': empresa,
            'setor': setor,
            'veiculo_id': placa,
            'modelo_veiculo': modelo_veiculo,
            'data_abertura': data_abertura,
            'data_encerramento': data_encerramento,
            'data_integracao': data_integracao,
            'descricao': descricao,
            'status': status,
            'flag_especial': parse_bool_flag(flag_str),
            'valor_pecas': parse_decimal_br(valor_pecas_str),
            'valor_servicos': parse_decimal_br(valor_servicos_str),
            'valor_total': parse_decimal_br(valor_total_str),
        }

        _, created = Manutencao.objects.update_or_create(
            numero_os=numero_os,
            defaults=defaults,
        )
        if created:
            inseridos += 1
        else:
            atualizados += 1

    return {
        'inseridos': inseridos,
        'atualizados': atualizados,
        'erros': erros,
    }
