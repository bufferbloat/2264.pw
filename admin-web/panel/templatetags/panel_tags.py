from django import template

register = template.Library()


@register.filter
def lookup(value, key):
    missing = {"views": None, "likes": None}
    return value.get(str(key), missing) if isinstance(value, dict) else missing
