import pandas as pd
from apps.veiculos.models import Veiculo


def importar_veiculos(file):
    df = pd.read_csv(file, encoding='utf-8', dtype=str).fillna('')
    df.columns = [c.strip() for c in df.columns]

    inseridos = 0
    atualizados = 0
    erros = []

    for _, row in df.iterrows():
        placa = str(row.get('Placa', '')).strip()
        if not placa:
            continue

        _, created = Veiculo.objects.update_or_create(
            placa=placa,
            defaults={
                'marca': str(row.get('Marca', '')).strip(),
                'modelo': str(row.get('Modelo', '')).strip(),
                'unidade': str(row.get('unidade', '')).strip(),
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
