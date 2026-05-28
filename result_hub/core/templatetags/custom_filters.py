from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def sum_values(values):
    return sum(values)

@register.filter
def divide(value, arg):
    try:
        return value / arg
    except (ZeroDivisionError, TypeError):
        return 0