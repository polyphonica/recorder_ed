"""
Context processors for accounts app.
Makes user verification status available in all templates.
"""

def email_verification_status(request):
    """
    Add email verification status to template context.
    """
    if request.user.is_authenticated:
        return {
            'user_email_verified': request.user.profile.email_verified,
        }
    return {
        'user_email_verified': True,  # Don't show banner for anonymous users
    }
