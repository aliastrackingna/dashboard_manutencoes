import pandas as pd
from apps.manutencoes.models import Manutencao, Orcamento
from .base import parse_decimal_br, parse_date_br


def importar_orcamentos(file):
    df = pd.read_csv(file, encoding='utf-8', dtype=str).fillna('')

    inseridos = 0
    atualizados = 0
    erros = []

    for idx, row in df.iterrows():
        numero_os = str(row.get('numero_os', '')).strip()
        codigo_str = str(row.get('codigo_orcamento', '')).strip()

        if not codigo_str:
            continue

        try:
            codigo_orcamento = int(codigo_str)
        except ValueError:
            erros.append({
                'linha': idx + 2,
                'tipo': 'VALOR_INVALIDO',
                'motivo': f"codigo_orcamento inválido: '{codigo_str}'",
            })
            continue

        try:
            manutencao = Manutencao.objects.get(numero_os=numero_os)
        except Manutencao.DoesNotExist:
            erros.append({
                'linha': idx + 2,
                'tipo': 'FK_AUSENTE',
                'entidade': 'Orcamento',
                'chave': codigo_orcamento,
                'motivo': f"OS '{numero_os}' não encontrada",
            })
            continue

        data = parse_date_br(str(row.get('data', '')).strip())
        oficina = str(row.get('oficina', '')).strip()
        valor = parse_decimal_br(str(row.get('valor', '')).strip())
        status = str(row.get('status', '')).strip()

        _, created = Orcamento.objects.update_or_create(
            codigo_orcamento=codigo_orcamento,
            defaults={
                'manutencao': manutencao,
                'data': data,
                'oficina': oficina,
                'valor': valor,
                'status': status,
            },
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
