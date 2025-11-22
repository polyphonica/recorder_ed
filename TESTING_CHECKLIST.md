# Refactoring Testing Checklist

## Priority 1: Stripe Payment Changes (Task #5)

These are the most critical to test as they involve actual payments.

### 1. Exam Payment Flow (Private Teaching)
**File Changed:** `apps/private_teaching/views.py:1969-2010`

**Test Steps:**
1. Log in as a student
2. Register for an exam that requires payment
3. Click "Pay for Exam"
4. Verify Stripe checkout session is created
5. Complete payment (use Stripe test card: 4242 4242 4242 4242)
6. Verify payment success redirect
7. Verify exam is marked as paid
8. Check that `stripe_checkout_session_id` is saved to exam record

**What Changed:**
- Now uses `stripe_service.create_checkout_session()` instead of direct Stripe API call
- Should work identically, just cleaner code

**Expected Behavior:** No changes - payment flow should work exactly as before

---

### 2. Workshop Cancellation with Refund
**File Changed:** `apps/workshops/views.py:741-787`

**Test Steps:**
1. Log in as a student
2. Register for a workshop (7+ days in future)
3. Pay for the workshop
4. Cancel the registration (while still 7+ days away)
5. Verify refund is processed automatically
6. Check for success message about refund
7. Verify `StripePayment` record is marked as refunded

**What Changed:**
- Now uses `stripe_service.create_refund()` instead of direct Stripe API call
- Automatically formats amount (no manual pence conversion)
- Added `reason='requested_by_customer'`

**Expected Behavior:** No changes - refund should process as before

---

## Priority 2: Admin Interface Changes (Phase 2)

### 3. Workshop Admin - Price Display
**File Changed:** `apps/workshops/admin.py`

**Test Steps:**
1. Log in as admin/superuser
2. Go to Django admin → Workshops → Workshops
3. Verify price column shows:
   - "Free" in green for free workshops
   - "£50.00" format for paid workshops
4. Check that instructor name displays as "Full Name (username)"

**What Changed:**
- Now uses `PriceDisplayMixin` for price_display
- Now uses `InstructorQuerysetMixin` for query optimization
- Now uses `UserDisplayMixin` for instructor name formatting

**Expected Behavior:** Should look identical, possibly faster due to query optimization

---

### 4. Course Admin - Instructor Display
**File Changed:** `apps/courses/admin.py`

**Test Steps:**
1. Go to Django admin → Courses → Courses
2. Verify instructor names display correctly
3. Check that queryset is optimized (fewer database queries)

**What Changed:**
- Now uses `InstructorQuerysetMixin` for automatic query optimization

**Expected Behavior:** Same display, better performance

---

## Priority 3: Notification System (Phase 1)

### 5. Course Enrollment Notifications
**File Changed:** `apps/courses/notifications.py`

**Test Steps:**
1. Enroll a student in a course
2. Check email sent to student
3. Verify student name is correct (especially for child profiles)
4. Verify course URL works
5. Check email sent to instructor
6. Verify guardian info shows for child enrollments

**What Changed:**
- Now uses `build_detail_url()` for cleaner URL building
- Now uses `enrollment.student_name` property instead of manual logic
- Now uses `enrollment.is_for_child` property

**Expected Behavior:** Emails should be identical

---

### 6. Workshop Registration Notifications
**File Changed:** `apps/workshops/notifications.py`

**Test Steps:**
1. Register for a workshop
2. Check registration confirmation email
3. Verify workshop URL works
4. Verify student name is correct for child registrations

**What Changed:**
- Now uses `build_detail_url()` and `build_action_url()` helpers
- Now uses `registration.is_for_child` property

**Expected Behavior:** Emails should be identical

---

### 7. Private Lesson Exam Notifications
**File Changed:** `apps/private_teaching/notifications.py`

**Test Steps:**
1. Register for an exam
2. Check exam registration email
3. Verify exam detail URL works

**What Changed:**
- Now uses `build_action_url()` helper

**Expected Behavior:** Emails should be identical

---

## Priority 4: Child Profile Handling

### 8. Child Enrollment (Courses)
**Test Steps:**
1. Log in as parent/guardian
2. Add a child profile if not exists
3. Enroll the child in a course
4. Verify enrollment shows child's name (not guardian's)
5. Check notification email uses child's name

**What Changed:**
- Now consistently uses `is_for_child` and `student_name` properties

**Expected Behavior:** Should work identically

---

### 9. Child Registration (Workshops)
**Test Steps:**
1. Log in as parent/guardian
2. Register a child for a workshop
3. Verify registration shows child's name
4. Check notification email

**What Changed:**
- Now consistently uses `is_for_child` property

**Expected Behavior:** Should work identically

---

## Priority 5: File Attachments

### 10. Lesson Attachments
**File Changed:** `apps/courses/models.py` (LessonAttachment now inherits from BaseAttachment)

**Test Steps:**
1. Go to a course lesson with attachments
2. Verify file size displays correctly (e.g., "2.3 MB")
3. Verify file extension displays correctly (e.g., "pdf")
4. Try uploading a new attachment as instructor
5. Verify it saves correctly

**What Changed:**
- LessonAttachment now inherits from BaseAttachment
- Migration added `updated_at` field

**Expected Behavior:** Should work identically

---

## Quick Smoke Tests

Run these first to catch any obvious issues:

```bash
# 1. Check for any Python syntax errors
python manage.py check

# 2. Run migrations (if any)
python manage.py migrate

# 3. Test Django admin loads
# Visit /admin/ and verify it loads without errors

# 4. Test imports work
python manage.py shell -c "
from apps.payments.stripe_service import create_checkout_session, create_refund
from apps.core.admin import UserDisplayMixin, PriceDisplayMixin, InstructorQuerysetMixin
from apps.courses.models import LessonAttachment
from apps.core.models import BaseAttachment
print('✓ All critical imports successful')
"
```

---

## Database Queries to Verify

```python
# In Django shell (python manage.py shell)

# Check LessonAttachment inherits correctly
from apps.courses.models import LessonAttachment
from apps.core.models import BaseAttachment
print(f"LessonAttachment inherits from BaseAttachment: {issubclass(LessonAttachment, BaseAttachment)}")

# Check if updated_at field was added
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='courses_lessonattachment'")
    columns = [row[0] for row in cursor.fetchall()]
    print(f"updated_at exists: {'updated_at' in columns}")
```

---

## Rollback Plan

If any issues are found:

```bash
# Revert last commit (Task #5)
git revert 16a4d91

# Or revert all refactoring (Phases 1-3)
git revert 16a4d91  # Task #5
git revert 05d9574  # Phase 2
git revert d92f3f7  # Phase 1
```

---

## Notes

- **No behavioral changes expected** - All refactoring maintains existing functionality
- **Focus on Stripe tests** - These are the most critical (real money involved!)
- **Child profile tests** - Important for data integrity
- **Admin tests** - Visual checks, low risk
- **Notification tests** - Check URLs work, content is correct

## Test Priority Order

1. **Stripe payments & refunds** (CRITICAL - involves money)
2. **Child profile handling** (Important - data integrity)
3. **Notifications** (Important - user communication)
4. **Admin interface** (Low risk - visual only)
5. **File attachments** (Low risk - simple inheritance)
