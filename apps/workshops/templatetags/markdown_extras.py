"""
Template tags for rendering Markdown content
"""
from django import template
from django.utils.safestring import mark_safe
import markdown as md

register = template.Library()


@register.filter(name='markdown')
def markdown_filter(text):
    """
    Convert markdown text to HTML.

    Usage: {{ content|markdown }}
    """
    if not text:
        return ''

    # Configure markdown with extensions for better rendering
    html = md.markdown(
        text,
        extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
        ]
    )

    return mark_safe(html)
