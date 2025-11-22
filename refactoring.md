# Refactoring Opportunities

**Total Estimated Line Reduction:** ~1,400 - 1,800 lines (approximately 10-15% of core app code)

---

## **1. Consolidate URL Helper Methods in Notification Services**

**Impact:** ~100-150 lines could be eliminated
**Files Affected:** 7 notification files (workshops, courses, private_teaching, support, messaging, lessons, core)
**Difficulty:** Easy

### What's Duplicated
- Each notification file has private `_build_*_url()` helper methods that all call `build_absolute_url()` from the base class
- Examples: `_build_confirmation_url()`, `_build_workshop_url()`, `_build_materials_url()`, `_build_registrations_url()`
- Found 54 occurrences of URL building patterns across notification files

### Current Pattern
```python
# workshops/notifications.py
@staticmethod
def _build_confirmation_url(registration):
    return WaitlistNotificationService.build_absolute_url(
        'workshops:confirm_promotion',
        kwargs={'registration_id': registration.id},
        use_https=False
    )

# Similar methods duplicated across all notification services
```

### Refactoring Approach
Create a `URLBuilderMixin` in `apps/core/notifications.py` with common URL patterns:

```python
class URLBuilderMixin:
    @classmethod
    def build_detail_url(cls, url_name, obj, slug_field='slug'):
        """Build URL for detail pages"""
        return cls.build_absolute_url(url_name, kwargs={slug_field: getattr(obj, slug_field)})

    @classmethod
    def build_action_url(cls, url_name, obj, id_field='id'):
        """Build URL for action pages"""
        return cls.build_absolute_url(url_name, kwargs={f'{id_field}': getattr(obj, id_field)})
```

---

## **2. Extract Common Student/Guardian Name Display Logic**

**Impact:** ~150-200 lines could be eliminated
**Files Affected:** workshops/models.py, courses/models.py, private_teaching/models.py, and 6+ admin files
**Difficulty:** Easy

### What's Duplicated
- Found 73 occurrences of `get_full_name() or username` pattern across the codebase
- Every model with child_profile support duplicates name display logic
- Admin files duplicate instructor/student name display methods

### Current Pattern
```python
# Duplicated in workshops/models.py, courses/models.py, private_teaching/models.py
@property
def student_name(self):
    if self.child_profile:
        return self.child_profile.full_name
    return self.student.get_full_name() or self.student.username
```

### Refactoring Approach
The `PayableModel` already has this! But it's not being used consistently. Standardize all models to use inherited properties and create admin display helpers:

```python
# apps/core/admin.py - Add new mixin
class UserDisplayMixin:
    @staticmethod
    def format_user_display(user):
        """Standard user display: Full Name (username)"""
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name} ({user.username})"
        elif user.first_name or user.last_name:
            return f"{user.first_name}{user.last_name} ({user.username})"
        return user.username
```

---

## **3. Consolidate Notification Error Handling and Logging**

**Impact:** ~200+ lines could be eliminated
**Files Affected:** All 7 notification files
**Difficulty:** Medium

### What's Duplicated
- 60+ logging statements with nearly identical patterns
- Every notification method has try/except with same structure
- Duplicate email validation patterns (checking for student email)

### Current Pattern
```python
# Repeated ~40 times across notification files
try:
    if not enrollment.student or not enrollment.student.email:
        logger.warning(f"No student email found for enrollment {enrollment.id}")
        return False
    # ... send email ...
    return True
except Exception as e:
    logger.error(f"Failed to send enrollment confirmation to student: {str(e)}")
    return False
```

### Refactoring Approach
Create a decorator in `BaseNotificationService`:

```python
class BaseNotificationService:
    @staticmethod
    def notification_handler(email_attr='student.email', entity_name='entity'):
        """Decorator for notification methods with standard error handling"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    entity = args[0]  # First arg is typically the model instance
                    email = rgetattr(entity, email_attr)
                    if not email:
                        logger.warning(f"No email found for {entity_name} {entity.id}")
                        return False
                    result = func(*args, **kwargs)
                    if result:
                        logger.info(f"Sent notification for {entity_name} {entity.id}")
                    return result
                except Exception as e:
                    logger.error(f"Failed to send notification: {str(e)}")
                    return False
            return wrapper
        return decorator
```

---

## **4. Create Shared File Property Methods**

**Impact:** ~50-80 lines could be eliminated
**Files Affected:** courses/models.py, workshops/models.py, and others
**Difficulty:** Easy

### What's Duplicated
- 13 instances of `file_size` and `file_extension` property methods
- Exact same implementation across `LessonAttachment`, `WorkshopMaterial`
- Already exists in `BaseAttachment` but not being used!

### Current Situation
```python
# Duplicated in courses/models.py (LessonAttachment)
@property
def file_size(self):
    if self.file:
        try:
            size = self.file.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except (OSError, ValueError):
            return "Unknown size"
    return "0 B"

# Identical code in workshops/models.py (WorkshopMaterial)
```

### Refactoring Approach
- `LessonAttachment` should inherit from `BaseAttachment` (it already has UUID, title, file, order, timestamps)
- `WorkshopMaterial` already has the methods - remove duplication
- Ensure all file-based models use the base class

---

## **5. Standardize Stripe Payment Field Patterns**

**Impact:** ~100+ lines across models
**Files Affected:** PayableModel is good, but 64 references to stripe fields show inconsistent usage
**Difficulty:** Medium

### What's Duplicated
- Stripe field definitions repeated outside of `PayableModel`
- Payment status handling logic duplicated across views
- 14 instances of Stripe checkout session creation with similar code

### Current Pattern
```python
# Found in Order model (private_teaching) - duplicates PayableModel fields
stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True)
```

### Refactoring Approach
1. Ensure `Order` model inherits from `PayableModel` (or create a `BaseOrder` that does)
2. Extract checkout session creation to a shared service:

```python
# apps/core/services.py
class StripeCheckoutService:
    @staticmethod
    def create_checkout_session(line_items, success_url, cancel_url, metadata=None):
        """Centralized Stripe checkout session creation"""
        # Common session creation logic
```

---

## **6. Create Base Admin Configurations**

**Impact:** ~300-500 lines could be eliminated
**Files Affected:** workshops/admin.py (500 lines), courses/admin.py (709 lines), private_teaching/admin.py (301 lines)
**Difficulty:** Medium

### What's Duplicated
- `InstructorChoiceField` only defined once but pattern could be reused
- Similar fieldset structures across all admins (Basic Info, Media, Pricing, Timestamps)
- Duplicate display methods: `instructor_name()`, `price_display()`, `student_name()`
- QuerySet optimization patterns (`select_related`, `prefetch_related`)

### Current Pattern
```python
# workshops/admin.py
class InstructorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name} ({obj.username})"
        # ... duplicated logic

# Similar pattern could be used in courses/admin.py and private_teaching/admin.py
```

### Refactoring Approach
Move to `apps/core/admin.py`:

```python
class InstructorChoiceField(forms.ModelChoiceField):
    """Reusable instructor selection with full name display"""
    # Move from workshops/admin.py

class BaseInstructorModelAdmin(admin.ModelAdmin):
    """Base admin for models with instructor field"""
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('instructor')

    def instructor_display(self, obj):
        """Standard instructor name display"""
        return UserDisplayMixin.format_user_display(obj.instructor)
    instructor_display.short_description = 'Instructor'

class BasePricedModelAdmin(admin.ModelAdmin):
    """Base admin for models with pricing"""
    def price_display(self, obj):
        if obj.is_free:
            return format_html('<span style="color: green;">Free</span>')
        return f"£{obj.price}"
```

---

## **7. Extract Common Permission/Access Control Patterns**

**Impact:** ~200-300 lines across views
**Files Affected:** All view files (7,229 total lines across 3 main apps)
**Difficulty:** Medium

### What's Duplicated
- 91 decorator usages (`@login_required`, `LoginRequiredMixin`)
- Repeated ownership checks (user owns course/workshop/lesson)
- Similar enrollment verification logic

### Current Pattern
```python
# Repeated across views.py files
def some_view(request, slug):
    workshop = get_object_or_404(Workshop, slug=slug)
    if workshop.instructor != request.user:
        messages.error(request, "You don't own this workshop")
        return redirect('workshops:list')
```

### Refactoring Approach
Create generic ownership mixins in `apps/core/mixins.py`:

```python
class OwnershipRequiredMixin(LoginRequiredMixin):
    """Require user to own the object"""
    ownership_field = 'instructor'  # or 'owner', 'teacher', etc.

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if getattr(obj, self.ownership_field) != request.user:
            messages.error(request, f"You don't have permission to access this {self.model.__name__}")
            return redirect(self.permission_denied_url)
        return super().dispatch(request, *args, **kwargs)
```

---

## **8. Consolidate Child Profile Support Logic**

**Impact:** ~100-150 lines
**Files Affected:** 6 model files with 64 child_profile references
**Difficulty:** Easy

### What's Duplicated
- `PayableModel` already provides `is_for_child`, `student_name`, `guardian` properties
- But many models still define `is_child_enrollment`, `is_child_registration`, `is_child_request` as duplicates
- Admin display logic for child vs adult enrollments repeated

### Current Pattern
```python
# workshops/models.py
@property
def is_child_registration(self):
    """Alias for is_for_child for backward compatibility"""
    return self.is_for_child

# courses/models.py
@property
def is_child_enrollment(self):
    """Alias for is_for_child for backward compatibility"""
    return self.is_for_child

# private_teaching/models.py
@property
def is_child_request(self):
    """Alias for is_for_child for backward compatibility"""
    return self.is_for_child
```

### Refactoring Approach
1. Keep ONE alias in `PayableModel` for backward compatibility
2. Update all code to use `is_for_child` consistently
3. Remove redundant aliases from subclasses
4. Add deprecation warnings to encourage migration

---

## **9. Create Shared Context Builder for Notifications**

**Impact:** ~150+ lines
**Files Affected:** All 7 notification files
**Difficulty:** Medium

### What's Duplicated
- Every notification builds similar context dictionaries
- Common fields like `site_name`, user names, URLs repeated
- Email template pattern (Subject: line extraction) handled the same way

### Current Pattern
```python
# Repeated pattern across all notification methods
context = {
    'enrollment': enrollment,
    'course': enrollment.course,
    'student_name': student_name,
    'is_child_enrollment': is_child_enrollment,
    'course_url': course_url,
    'my_courses_url': my_courses_url,
}
```

### Refactoring Approach
Create context builder helpers in `BaseNotificationService`:

```python
class BaseNotificationService:
    @staticmethod
    def build_base_context(entity, **extra):
        """Build base context for all notifications"""
        context = {
            'site_name': BaseNotificationService.get_site_name(),
            **extra
        }
        return context

    @staticmethod
    def add_user_context(context, user, role='user'):
        """Add user-related context fields"""
        context[f'{role}_name'] = user.get_full_name() or user.username
        context[f'{role}_email'] = user.email
        context[role] = user
        return context
```

---

## **10. Standardize Cancellation/Refund Policy Logic**

**Impact:** ~200+ lines
**Files Affected:** courses/models.py, workshops/models.py, private_teaching/models.py
**Difficulty:** Medium

### What's Duplicated
- `BaseCancellationRequest` provides framework but each subclass duplicates similar refund calculation logic
- Time-based eligibility checks (7-day trial, 48-hour notice) have similar patterns
- Three different implementations of essentially time-delta + payment-status checks

### Current Pattern
```python
# courses/models.py - 7-day trial
def calculate_refund_eligibility(self):
    trial_period_days = 7
    enrollment_date = self.enrollment.enrolled_at
    cutoff_date = enrollment_date + timedelta(days=trial_period_days)
    # ... calculate

# private_teaching/models.py - 48-hour notice
def calculate_refund_eligibility(self):
    # Must be within 48-hour policy
    if not self.is_within_policy:
        eligible = False
    # ... calculate with platform fee
```

### Refactoring Approach
Create a refund policy framework in `BaseCancellationRequest`:

```python
class RefundPolicy:
    """Base refund policy framework"""
    def check_time_window(self, reference_date, window_days, comparison='before'):
        """Check if current time is within window"""
        # Shared logic

    def calculate_refund_amount(self, original_amount, fee_rate=0):
        """Calculate refund amount with optional fees"""
        # Shared logic

class TrialPeriodRefundPolicy(RefundPolicy):
    """7-day trial period policy"""
    window_days = 7

class AdvanceNoticeRefundPolicy(RefundPolicy):
    """48-hour advance notice policy"""
    window_hours = 48
```

---

## **Implementation Strategy**

### Phase 1: Easy Wins (Items 1, 2, 4, 8)
- **Estimated Time:** 1-2 days
- **Line Reduction:** 300-400 lines
- **Risk:** Low - mostly consolidating existing patterns
- **Testing:** Minimal - no behavioral changes

### Phase 2: Medium Effort (Items 3, 6, 9)
- **Estimated Time:** 3-5 days
- **Line Reduction:** 600-800 lines
- **Risk:** Medium - changing notification and admin patterns
- **Testing:** Comprehensive notification testing required

### Phase 3: Architectural Improvements (Items 5, 7, 10)
- **Estimated Time:** 3-5 days
- **Line Reduction:** 400-600 lines
- **Risk:** Medium-High - changing core patterns and payment logic
- **Testing:** Full regression testing needed

---

## **Priority Order**

1. **Items 1-4** (Easy wins) - Start here for immediate impact
2. **Items 5-7** (Architectural improvements) - Better developer experience
3. **Items 8-10** (Maintainability) - Reduce technical debt

---

## **Testing Requirements**

- **Notification Refactoring:** Comprehensive email sending tests (most critical user-facing feature)
- **Admin Changes:** Lower risk - mainly developer experience improvements
- **Model Changes:** Require migration strategy and backward compatibility
- **View/Permission Changes:** Full integration testing across all user roles

---

## **Success Metrics**

- **Code Reduction:** 1,400-1,800 lines eliminated (10-15% of core app code)
- **Maintainability:** Fewer files to update when making changes
- **Consistency:** Single source of truth for common patterns
- **Developer Experience:** Easier onboarding and feature development
