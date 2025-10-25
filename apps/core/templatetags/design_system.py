from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()


@register.inclusion_tag('components/stat_card.html')
def stat_card(icon, value, label, color='primary'):
    """Render a stat card component"""
    return {
        'icon': icon,
        'value': value,
        'label': label,
        'color': color,
    }


@register.inclusion_tag('components/badge.html')
def badge(text, color='neutral', size='md'):
    """Render a badge component"""
    return {
        'text': text,
        'color': color,
        'size': size,
    }


@register.inclusion_tag('components/button.html')
def button(text, variant='primary', color='primary', url=None, type='button', size='md', extra_classes='', icon=None):
    """Render a button component with various styles and options"""
    return {
        'text': text,
        'variant': variant,
        'color': color,
        'url': url,
        'type': type,
        'size': size,
        'extra_classes': extra_classes,
        'icon': icon,
    }


@register.inclusion_tag('components/card.html')
def card(title=None, content=None, variant='default', **kwargs):
    """Render a comprehensive card component with multiple variations"""
    return {
        'title': title,
        'content': content,
        'variant': variant,
        **kwargs
    }


@register.inclusion_tag('components/alert.html')
def alert(message, type='info', dismissible=True, icon=None):
    """Render an alert/notification component"""
    return {
        'message': message,
        'type': type,
        'dismissible': dismissible,
        'icon': icon,
    }


@register.inclusion_tag('components/modal.html')
def modal(id, title, content=None, size='md'):
    """Render a modal component"""
    return {
        'id': id,
        'title': title,
        'content': content,
        'size': size,
    }


@register.inclusion_tag('components/tabs.html')
def tabs(tabs_data, active_tab=None):
    """Render a tabs component"""
    return {
        'tabs': tabs_data,
        'active_tab': active_tab,
    }


@register.inclusion_tag('components/dropdown.html')
def dropdown(button_text, items, position='bottom'):
    """Render a dropdown component"""
    return {
        'button_text': button_text,
        'items': items,
        'position': position,
    }


@register.inclusion_tag('components/progress.html')
def progress_bar(value, max_value=100, color='primary', size='md', label=None):
    """Render a progress bar component"""
    percentage = (value / max_value) * 100 if max_value > 0 else 0
    return {
        'value': value,
        'max_value': max_value,
        'percentage': percentage,
        'color': color,
        'size': size,
        'label': label,
    }


@register.inclusion_tag('components/breadcrumb.html')
def breadcrumb(items):
    """Render a breadcrumb navigation component"""
    return {
        'items': items,
    }


@register.inclusion_tag('components/pagination.html')
def pagination(current_page, total_pages, url_pattern='?page={}'):
    """Render pagination component"""
    return {
        'current_page': current_page,
        'total_pages': total_pages,
        'url_pattern': url_pattern,
        'pages': range(1, total_pages + 1),
    }


@register.simple_tag
def icon(name, size='w-5 h-5', extra_classes=''):
    """Render an icon using Heroicons"""
    icons = {
        'users': '<svg class="{size} {extra}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z"></path></svg>',
        'book-open': '<svg class="{size} {extra}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>',
        'award': '<svg class="{size} {extra}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"></path></svg>',
        'calendar': '<svg class="{size} {extra}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>',
        'star': '<svg class="{size} {extra}" fill="currentColor" viewBox="0 0 24 24"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path></svg>',
        'x': '<svg class="{size} {extra}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>',
        'check': '<svg class="{size} {extra}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>',
        'info': '<svg class="{size} {extra}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
        'warning': '<svg class="{size} {extra}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z"></path></svg>',
        'chevron-down': '<svg class="{size} {extra}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>',
        'menu': '<svg class="{size} {extra}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>',
    }
    
    icon_html = icons.get(name, icons['info'])
    return mark_safe(icon_html.format(size=size, extra=extra_classes))


@register.filter
def json_script(value):
    """Convert Python object to JSON for use in Alpine.js"""
    return mark_safe(json.dumps(value))