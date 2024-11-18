from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag
def query_string(request, **kwargs):
    """
    Modifies the current query string, adding or updating specified parameters.
    """
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            updated.pop(key, None)  # Remove key if value is None
        else:
            updated[key] = value
    return f"?{urlencode(updated)}"