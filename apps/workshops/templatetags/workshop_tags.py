from django import template

register = template.Library()

@register.filter
def split(value, separator=','):
    """Split a string by separator and return a list"""
    if value:
        return [item.strip() for item in value.split(separator) if item.strip()]
    return []

@register.filter
def join_with(value, separator=', '):
    """Join a list with separator"""
    if value:
        return separator.join(value)
    return ''

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key)

@register.filter
def get_user_registration_id(session, user):
    """Get the registration ID for a user in a specific session"""
    from apps.workshops.models import WorkshopRegistration
    try:
        registration = WorkshopRegistration.objects.get(
            session=session,
            student=user
        )
        return registration.id
    except WorkshopRegistration.DoesNotExist:
        return None