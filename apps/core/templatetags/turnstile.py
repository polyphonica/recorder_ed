from django import template

from apps.core.turnstile import widget_html

register = template.Library()


@register.simple_tag
def turnstile_widget():
    """Turnstile widget for hand-written forms; renders nothing when keys aren't set"""
    return widget_html()
