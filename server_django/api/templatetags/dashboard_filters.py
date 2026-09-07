from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Retorna um item de um dicionário pela chave"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def split(string, delimiter):
    """Split uma string por um delimitador"""
    if not string:
        return []
    return string.split(delimiter)
