import pandas as pd

from apps.manutencoes.models import Manutencao
from .base import parse_datetime_br


def importar_complemento_manutencao(file):
    df = pd.read_csv(file, sep=';', header=None, encoding='utf-8', dtype=str).fillna('')

    atualizados = 0
    erros = []

    for idx, row in df.iterrows():
        valores = list(row)
        numero_os = str(valores[0]).strip()

        if not numero_os:
            erros.append({
                'linha': idx + 1,
                'tipo': 'CAMPO_OBRIGATORIO',
                'motivo': 'Número OS vazio',
            })
            continue

        try:
            manutencao = Manutencao.objects.get(numero_os=numero_os)
        except Manutencao.DoesNotExist:
            erros.append({
                'linha': idx + 1,
                'tipo': 'FK_AUSENTE',
                'motivo': f"OS '{numero_os}' não encontrada",
            })
            continue

        inicio_execucao = parse_datetime_br(str(valores[3]).strip()) if len(valores) > 3 else None
        fim_execucao = parse_datetime_br(str(valores[4]).strip()) if len(valores) > 4 else None

        manutencao.inicio_execucao = inicio_execucao
        manutencao.fim_execucao = fim_execucao
        manutencao.save(update_fields=['inicio_execucao', 'fim_execucao'])
        atualizados += 1

    return {
        'atualizados': atualizados,
        'erros': erros,
    }
