from datetime import datetime

import pandas as pd

from apps.multas.models import Multa
from apps.veiculos.models import Veiculo
from .base import parse_date_br, parse_decimal_br


def importar_multas(file):
    df = pd.read_csv(file, sep=';', encoding='utf-8', dtype=str).fillna('')
    df.columns = [c.strip() for c in df.columns]

    inseridos = 0
    ignorados = 0
    erros = []

    for idx, row in df.iterrows():
        auto_infracao = str(row.get('Auto Infração', row.get('Auto Infracao', ''))).strip()
        if not auto_infracao:
            erros.append({
                'linha': idx + 2,
                'tipo': 'CAMPO_OBRIGATORIO',
                'motivo': 'Auto Infração vazio',
            })
            continue

        if Multa.objects.filter(auto_infracao=auto_infracao).exists():
            ignorados += 1
            continue

        placa = str(row.get('Placa', '')).strip()
        if not placa:
            erros.append({
                'linha': idx + 2,
                'tipo': 'CAMPO_OBRIGATORIO',
                'motivo': f"Placa vazia para auto infração '{auto_infracao}'",
            })
            continue

        if not Veiculo.objects.filter(placa=placa).exists():
            erros.append({
                'linha': idx + 2,
                'tipo': 'FK_AUSENTE',
                'motivo': f"Veículo '{placa}' não encontrado para auto infração '{auto_infracao}'",
            })
            continue

        data_infracao = parse_date_br(
            str(row.get('Data Infração', row.get('Data Infracao', ''))).strip()
        )
        if not data_infracao:
            erros.append({
                'linha': idx + 2,
                'tipo': 'DATA_INVALIDA',
                'motivo': f"Data infração inválida para auto infração '{auto_infracao}'",
            })
            continue

        hora_str = str(row.get('Hora Infração', row.get('Hora Infracao', ''))).strip()
        hora_infracao = None
        if hora_str:
            try:
                hora_infracao = datetime.strptime(hora_str, '%H:%M').time()
            except ValueError:
                try:
                    hora_infracao = datetime.strptime(hora_str, '%H:%M:%S').time()
                except ValueError:
                    pass

        orgao = str(row.get('Orgão Autuador', row.get('Orgao Autuador', ''))).strip()
        descricao = str(row.get('Descrição da Infração', row.get('Descricao da Infracao', ''))).strip()
        local = str(row.get('Local Infração', row.get('Local Infracao', ''))).strip()
        data_notif_str = str(row.get('Data da Notif. de Autuação', row.get('Data da Notif. de Autuacao', ''))).strip()
        data_notificacao = parse_date_br(data_notif_str)
        valor = parse_decimal_br(
            str(row.get('Valor da Multa', '')).strip()
        )

        Multa.objects.create(
            auto_infracao=auto_infracao,
            veiculo_id=placa,
            orgao_autuador=orgao,
            data_infracao=data_infracao,
            hora_infracao=hora_infracao,
            descricao_infracao=descricao,
            local_infracao=local,
            data_notificacao=data_notificacao,
            valor=valor,
        )
        inseridos += 1

    return {
        'inseridos': inseridos,
        'ignorados': ignorados,
        'erros': erros,
    }
