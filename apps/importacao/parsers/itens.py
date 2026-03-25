import pandas as pd
from apps.manutencoes.models import Orcamento, ItemOrcamento
from .base import parse_decimal_br, parse_date_br


def importar_itens(file):
    df = pd.read_csv(file, encoding='utf-8', dtype=str).fillna('')

    inseridos = 0
    erros = []
    orcamentos_processados = set()

    for idx, row in df.iterrows():
        codigo_str = str(row.get('codigo_orcamento', '')).strip()

        if not codigo_str:
            continue

        try:
            codigo_orcamento = int(codigo_str.replace('.', ''))
        except ValueError:
            erros.append({
                'linha': idx + 2,
                'tipo': 'VALOR_INVALIDO',
                'motivo': f"codigo_orcamento inválido: '{codigo_str}'",
            })
            continue

        try:
            orcamento = Orcamento.objects.get(codigo_orcamento=codigo_orcamento)
        except Orcamento.DoesNotExist:
            erros.append({
                'linha': idx + 2,
                'tipo': 'FK_AUSENTE',
                'entidade': 'ItemOrcamento',
                'chave': codigo_orcamento,
                'motivo': f"Orçamento '{codigo_orcamento}' não encontrado",
            })
            continue

        # Delete+reinsert strategy: delete all items for this orcamento on first encounter
        if codigo_orcamento not in orcamentos_processados:
            orcamento.itens.all().delete()
            orcamentos_processados.add(codigo_orcamento)

        ItemOrcamento.objects.create(
            orcamento=orcamento,
            tipo=str(row.get('tipo', '')).strip(),
            grupo=str(row.get('grupo', '')).strip(),
            codigo_item=str(row.get('codigo_item', '')).strip(),
            descricao=str(row.get('descricao', '')).strip(),
            marca=str(row.get('marca', '')).strip(),
            valor_unit=parse_decimal_br(str(row.get('valor_unit', '')).strip()),
            qtd=parse_decimal_br(str(row.get('qtd', '')).strip()),
            total=parse_decimal_br(str(row.get('total', '')).strip()),
            garantia=parse_date_br(str(row.get('garantia', '')).strip()),
        )
        inseridos += 1

    return {
        'inseridos': inseridos,
        'atualizados': 0,
        'erros': erros,
    }
