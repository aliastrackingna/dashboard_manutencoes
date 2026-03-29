import re
import unicodedata

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


def normalizar_codigo_item(codigo_item):
    base = _sem_acentos(str(codigo_item or '').upper())
    return re.sub(r'[^A-Z0-9]', '', base)


def normalizar_descricao_item(descricao):
    base = _sem_acentos(str(descricao or '').upper())
    base = re.sub(r'[^A-Z0-9]+', ' ', base)
    tokens = [t for t in base.split() if t and t not in TOKEN_RUIDO]
    return ' '.join(tokens)


def construir_chave_item_canonica(tipo, codigo_item, descricao):
    tipo_norm = (tipo or '').strip().upper()[:3]
    codigo_norm = normalizar_codigo_item(codigo_item)
    descricao_norm = normalizar_descricao_item(descricao)

    if codigo_norm:
        chave = f'{tipo_norm}|COD:{codigo_norm}'
    else:
        chave = f'{tipo_norm}|DESC:{descricao_norm}'

    return {
        'codigo_item_normalizado': codigo_norm,
        'descricao_normalizada': descricao_norm,
        'chave_item_canonica': chave,
    }
