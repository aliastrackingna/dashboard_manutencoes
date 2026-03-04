from django import template

register = template.Library()


@register.filter
def brl(value):
    """Formata valor monetário no padrão brasileiro: 115.941,56"""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    formatted = f'{value:,.2f}'
    return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
