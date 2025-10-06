from django import template

register = template.Library()


@register.filter
def div(value, arg):
    try:
        val = float(value) / float(arg)
        return float(val.__floor__())
    except (ValueError, ZeroDivisionError):
        return 0
