# Refactoring Opportunities - Workshop Series Implementation

This document tracks code complexity and refactoring opportunities identified during the implementation of mandatory series cancellation functionality.

## 1. Series Detection Logic (HIGH PRIORITY)

**Location:**
- `apps/payments/views.py:378-399` (webhook handler)
- `apps/workshops/views.py:2205-2219` (free workshop checkout)

**Issue:** Series detection logic is duplicated in two places and requires querying all cart items to determine if they belong to a mandatory series.

**Current Complexity:**
```python
# Check if this is a mandatory series purchase by examining all cart items
cart_items = WorkshopCartItem.objects.select_related('session__workshop').filter(id__in=item_ids)
is_mandatory_series = False
series_registration_id = None
if len(item_ids) > 1:
    workshops = set(item.session.workshop for item in cart_items)
    if len(workshops) == 1:
        workshop = workshops.pop()
        if workshop.is_series and workshop.require_full_series_registration:
            is_mandatory_series = True
            series_registration_id = uuid.uuid4()
```

**Recommendation:**
1. Add `is_series_purchase` boolean field to `WorkshopCartItem` model
2. Set this flag when adding items via `AddSeriesToCartView`
3. Simplifies detection to: `if any(item.is_series_purchase for item in cart_items)`
4. Extract common logic to utility function: `detect_series_purchase(cart_items) -> tuple[bool, UUID|None]`

**Benefits:**
- Eliminates duplicate code
- Reduces database queries
- Makes intent explicit
- Easier to test

## 2. Registration Cancellation Logic (MEDIUM PRIORITY)

**Location:** `apps/workshops/views.py:679-859`

**Issue:** Single method handles both individual and series cancellations, resulting in a 180-line function with complex branching logic.

**Current Complexity:**
- Mixed concerns: validation, series detection, session management, refund processing, notifications
- Difficult to test individual behaviors
- Hard to follow execution flow

**Recommendation:**
Split into separate methods:
```python
def _cancel_registration(self, request, *args, **kwargs):
    registration = self._get_and_validate_registration(kwargs.get('registration_id'), request.user)
    if registration.series_registration_id and registration.session.workshop.require_full_series_registration:
        return self._cancel_series_registrations(request, registration)
    else:
        return self._cancel_single_registration(request, registration)

def _cancel_single_registration(self, request, registration): ...
def _cancel_series_registrations(self, request, registration): ...
def _process_refund(self, request, registrations_to_cancel): ...
def _promote_from_waitlist(self, session): ...
```

**Benefits:**
- Single responsibility per method
- Easier to test individual components
- Clearer execution flow
- Easier to maintain

## 3. Registration Grouping Logic (MEDIUM PRIORITY)

**Location:** `apps/workshops/views.py:1037-1083` (MyRegistrationsView.get_context_data)

**Issue:** Complex grouping logic in view method that would be better as a model manager method or utility function.

**Current Complexity:**
- Nested loops and conditional logic
- Mixes data transformation with view concerns
- Difficult to unit test without instantiating view

**Recommendation:**
Extract to model manager or utility:
```python
# In models.py or utils.py
class WorkshopRegistrationManager(models.Manager):
    def group_for_display(self, queryset):
        """Group registrations: mandatory series together, individuals separate."""
        grouped = []
        processed_series_ids = set()
        for registration in queryset:
            if self._should_group_as_series(registration, processed_series_ids):
                series_group = self._create_series_group(registration, queryset)
                grouped.append(series_group)
                processed_series_ids.add(registration.series_registration_id)
            else:
                grouped.append({'is_series': False, 'registration': registration})
        return grouped
```

**Benefits:**
- Testable without view context
- Reusable across different views
- Clearer separation of concerns
- Can be optimized independently

## 4. Refund Calculation Logic (LOW PRIORITY)

**Location:** `apps/workshops/views.py:766-855`

**Issue:** Refund eligibility and amount calculation mixed with Stripe API calls and user messaging.

**Recommendation:**
Extract to service class:
```python
class RefundService:
    def calculate_refund_eligibility(self, registrations, earliest_session_date):
        """Returns (eligible, refund_amount, days_until)"""
        ...

    def process_refund(self, stripe_payment_intent_id, amount):
        """Process refund via Stripe and update local records"""
        ...
```

**Benefits:**
- Easier to test refund logic
- Can be mocked in tests
- Clearer financial business logic

## 5. Template Complexity (LOW PRIORITY)

**Location:** `templates/workshops/my_registrations.html`

**Issue:** Large template with mixed concerns (individual and series registrations, JavaScript, styling).

**Recommendation:**
- Already partially addressed by extracting `_series_registration_card.html`
- Consider extracting individual registration card as well
- Move JavaScript to separate file: `static/js/workshop_registrations.js`
- Consider Vue.js or Alpine.js for more complex interactivity

**Benefits:**
- Easier to maintain templates
- Reusable components
- Better separation of concerns

## 6. Missing Abstractions

**Recommended New Models/Classes:**

### SeriesRegistrationGroup (Model)
Instead of just linking via UUID, consider a proper model:
```python
class SeriesRegistrationGroup(models.Model):
    """Groups registrations purchased together as a mandatory series"""
    id = UUIDField(primary_key=True)
    workshop = ForeignKey(Workshop)
    student = ForeignKey(User)
    created_at = DateTimeField(auto_now_add=True)
    total_paid = DecimalField()
    payment_intent_id = CharField()  # Shared Stripe payment
    status = CharField(choices=[...])  # active, cancelled, completed

class WorkshopRegistration(models.Model):
    series_group = ForeignKey(SeriesRegistrationGroup, null=True)  # Instead of series_registration_id
```

**Benefits:**
- First-class concept in the domain model
- Easier to query and analyze
- Can store series-level metadata
- Clearer relationship semantics

## Implementation Priority

1. **HIGH**: Add `is_series_purchase` flag to WorkshopCartItem (eliminates duplicate detection logic)
2. **MEDIUM**: Split cancellation method (improves testability and maintenance)
3. **MEDIUM**: Extract grouping logic to manager (enables reuse and testing)
4. **LOW**: Extract refund service (minor improvement)
5. **LOW**: Template refactoring (incremental improvement)
6. **FUTURE**: Consider SeriesRegistrationGroup model (major refactoring)

## Estimated Effort

- Item 1: 2-3 hours (migration + update 2 locations)
- Item 2: 3-4 hours (split method + write tests)
- Item 3: 2 hours (extract to manager + write tests)
- Item 4: 2 hours (create service class)
- Item 5: 3-4 hours (extract JS, create components)
- Item 6: 8-10 hours (new model + migration + update all references)

**Total for HIGH+MEDIUM priorities: ~9-11 hours**

## Testing Recommendations

Current implementation needs tests for:
1. Series detection in both webhook and free checkout paths
2. Cascade cancellation of all sessions in mandatory series
3. Refund calculation for series (sum of all session amounts)
4. Template rendering of grouped vs individual registrations
5. JavaScript modal behavior for series cancellations

## Notes

- All refactoring opportunities have been documented in code comments with "REFACTORING NOTE:" prefix
- Current implementation is functional but has technical debt
- Consider addressing HIGH priority items in next sprint
- MEDIUM priority items can be tackled incrementally
- SeriesRegistrationGroup model is a significant change that should be carefully planned
