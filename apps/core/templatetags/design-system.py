from django import template

register = template.Library()

@register.filter
def get_initials(user):
    """Get user initials for avatar"""
    if user.first_name and user.last_name:
        return f"{user.first_name[0]}{user.last_name[0]}".upper()
    return user.username[0].upper()

@register.inclusion_tag('components/stat_card.html')
def stat_card(icon, value, label, color='teaching'):
    """Render a stat card component"""
    return {
        'icon': icon,
        'value': value,
        'label': label,
        'color': color,
    }

@register.inclusion_tag('components/badge.html')
def badge(text, color='gray'):
    """Render a badge component"""
    return {
        'text': text,
        'color': color,
    }

@register.inclusion_tag('components/button.html')
def button(text, variant='primary', color='teaching', url=None, type='button', extra_classes=''):
    """Render a button component"""
    return {
        'text': text,
        'variant': variant,
        'color': color,
        'url': url,
        'type': type,
        'extra_classes': extra_classes,
    }
