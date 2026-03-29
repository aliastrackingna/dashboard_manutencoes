import re
import unicodedata

from django.db import migrations, models


TOKEN_RUIDO = {
    'PCA',
    'SRV',
    'PECA',
    'PECAS',
    'SERVICO',
    'SERVICOS',
    'UN',
    'UND',
    'UNID',
    'UNIT',
}


def _sem_acentos(valor):
    texto = unicodedata.normalize('NFKD', valor or '')
    return ''.join(ch for ch in texto if not unicodedata.combining(ch))


def _normalizar_codigo_item(codigo_item):
    base = _sem_acentos(str(codigo_item or '').upper())
    return re.sub(r'[^A-Z0-9]', '', base)


def _normalizar_descricao_item(descricao):
    base = _sem_acentos(str(descricao or '').upper())
    base = re.sub(r'[^A-Z0-9]+', ' ', base)
    tokens = [t for t in base.split() if t and t not in TOKEN_RUIDO]
    return ' '.join(tokens)


def _construir_chave_item_canonica(tipo, codigo_item, descricao):
    tipo_norm = (tipo or '').strip().upper()[:3]
    codigo_norm = _normalizar_codigo_item(codigo_item)
    descricao_norm = _normalizar_descricao_item(descricao)

    if codigo_norm:
        chave = f'{tipo_norm}|COD:{codigo_norm}'
    else:
        chave = f'{tipo_norm}|DESC:{descricao_norm}'

    return codigo_norm, descricao_norm, chave


def popular_campos_canonicos(apps, schema_editor):
    ItemOrcamento = apps.get_model('manutencoes', 'ItemOrcamento')

    for item in ItemOrcamento.objects.all().iterator():
        codigo_norm, descricao_norm, chave = _construir_chave_item_canonica(
            item.tipo,
            item.codigo_item,
            item.descricao,
        )
        ItemOrcamento.objects.filter(id=item.id).update(
            codigo_item_normalizado=codigo_norm,
            descricao_normalizada=descricao_norm,
            chave_item_canonica=chave,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('manutencoes', '0004_manutencao_data_integracao'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemorcamento',
            name='chave_item_canonica',
            field=models.CharField(blank=True, db_index=True, default='', max_length=420),
        ),
        migrations.AddField(
            model_name='itemorcamento',
            name='codigo_item_normalizado',
            field=models.CharField(blank=True, db_index=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='itemorcamento',
            name='descricao_normalizada',
            field=models.CharField(blank=True, db_index=True, default='', max_length=350),
        ),
        migrations.RunPython(popular_campos_canonicos, migrations.RunPython.noop),
    ]
