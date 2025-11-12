"""
Workshops app mixins - imports shared mixins from core
"""

from apps.core.mixins import InstructorRequiredMixin as BaseInstructorRequiredMixin
from apps.core.mixins import SuperuserRequiredMixin as BaseSuperuserRequiredMixin


class InstructorRequiredMixin(BaseInstructorRequiredMixin):
    """Workshop-specific instructor mixin - raises PermissionDenied"""
    raise_exception = True


class SuperuserRequiredMixin(BaseSuperuserRequiredMixin):
    """Workshop-specific superuser mixin - raises PermissionDenied"""
    raise_exception = True