import re
from decimal import Decimal, InvalidOperation
from datetime import datetime


def parse_decimal_br(valor: str) -> Decimal:
    """'1.234,56' → Decimal('1234.56')"""
    if not valor or not str(valor).strip():
        return Decimal('0')
    limpo = re.sub(r'[^\d,]', '', str(valor)).replace(',', '.')
    try:
        return Decimal(limpo) if limpo else Decimal('0')
    except InvalidOperation:
        return Decimal('0')


def parse_datetime_br(valor: str) -> datetime | None:
    """'04/02/2026 13:01' → datetime"""
    if not valor or not str(valor).strip():
        return None
    for fmt in ('%d/%m/%Y %H:%M', '%d/%m/%Y'):
        try:
            return datetime.strptime(str(valor).strip(), fmt)
        except ValueError:
            continue
    return None


def parse_date_br(valor: str):
    """'14/05/2026' → date"""
    if not valor or not str(valor).strip():
        return None
    try:
        return datetime.strptime(str(valor).strip(), '%d/%m/%Y').date()
    except ValueError:
        return None


def parse_bool_flag(valor: str) -> bool:
    """'S' → True, anything else → False"""
    return str(valor).strip().upper() == 'S'
