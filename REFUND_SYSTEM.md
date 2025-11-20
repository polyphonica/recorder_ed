# Refund Tracking System

## Overview
The refund tracking system automatically captures refunds processed through Stripe and updates the finance reporting system accordingly.

## How It Works

### 1. Automatic Refund Detection
When a refund is processed in Stripe (either manually via dashboard or programmatically via API), Stripe sends a `charge.refunded` webhook event to the platform.

### 2. Webhook Processing
The webhook handler (`apps/payments/views.py:StripeWebhookView.handle_refund()`) automatically:
- Identifies the original StripePayment record
- Extracts refund amount and refund ID from Stripe
- Marks the payment as refunded with timestamp
- Logs the refund for audit trail

### 3. Database Tracking
The `StripePayment` model tracks refund details:
- `status` - Changes from 'completed' to 'refunded'
- `refund_amount` - Amount refunded (supports partial refunds)
- `refunded_at` - Timestamp when refund was processed
- `stripe_refund_id` - Stripe's refund transaction ID

### 4. Finance Report Impact
Revenue calculations automatically exclude refunded payments:
- **Revenue Trend Graph**: Filters by `status='completed'`, excluding refunded payments
- **Main Revenue Summaries**: Query source tables (WorkshopRegistration, CourseEnrollment, Order) which are filtered by their own status fields
- **Admin Interface**: Shows refund amount and type (Full/Partial) in payment list

## Refund Types

### Full Refund
When the entire payment amount is refunded:
```python
payment.is_full_refund()  # Returns True
# refund_amount >= total_amount
```

### Partial Refund
When only part of the payment is refunded:
```python
payment.is_partial_refund()  # Returns True
# refund_amount < total_amount
```

## Workflow Example

### Workshop Cancellation with Refund
1. **Instructor cancels workshop session**
2. **Process refund via Stripe**:
   - Go to Stripe Dashboard → Payments
   - Find the payment and click "Refund"
   - Choose full or partial refund amount
3. **Stripe sends webhook**: `charge.refunded` event
4. **System automatically**:
   - Updates StripePayment status to 'refunded'
   - Records refund amount and timestamp
   - Logs transaction for audit trail
5. **Update registration status** (manual):
   - Set WorkshopRegistration.status = 'cancelled'
   - This removes it from revenue calculations

### Student Cancellation (7+ days before)
1. **Student clicks cancel on their registration**
2. **System updates**: WorkshopRegistration.status = 'cancelled'
3. **Process refund manually** in Stripe dashboard
4. **Webhook automatically** tracks the refund in StripePayment

## Finance Reporting

### What's Excluded from Revenue
- Payments with `status='refunded'` (StripePayment table)
- Registrations with `status='cancelled'` (WorkshopRegistration table)
- Enrollments with `is_active=False` (CourseEnrollment table)
- Orders without `payment_status='completed'` (Order table)

### Admin Interface
View refunds in Django Admin:
- **Payments → Stripe Payments**
- Filter by Status = 'Refunded'
- Columns show: Amount, Refund Amount, Status
- Detail view shows: Refund Type, Refund ID, Timestamp

## API Methods

### Mark Payment as Refunded
```python
from apps.payments.models import StripePayment

payment = StripePayment.objects.get(stripe_payment_intent_id='pi_xxx')
payment.mark_refunded(
    refund_amount=Decimal('25.00'),  # Optional, defaults to full amount
    stripe_refund_id='re_xxx'        # Optional
)
```

### Check Refund Status
```python
if payment.is_full_refund():
    print("Full refund processed")
elif payment.is_partial_refund():
    print(f"Partial refund: £{payment.refund_amount} of £{payment.total_amount}")
```

## Webhook Configuration

### Required Stripe Webhook Events
Ensure the following event is enabled in Stripe Dashboard:
- `charge.refunded`

### Existing Events (already configured)
- `checkout.session.completed`
- `payment_intent.succeeded`
- `payment_intent.payment_failed`

### Webhook Endpoint
URL: `https://www.recorder-ed.com/payments/webhook/`

## Migration

Run the migration to add refund tracking fields:
```bash
python manage.py migrate payments
```

This adds:
- `refund_amount` (DecimalField)
- `refunded_at` (DateTimeField)
- `stripe_refund_id` (CharField)

## Testing

### Test Refund Webhook Locally
1. Use Stripe CLI to forward webhooks:
```bash
stripe listen --forward-to localhost:8000/payments/webhook/
```

2. Process a test refund in Stripe Dashboard

3. Check logs for webhook processing:
```python
# Look for:
# "Stripe refund webhook: payment_intent=pi_xxx"
# "Processing refund: re_xxx, amount: £XX.XX"
# "Payment X marked as refunded. Original: £XX, Refunded: £XX, Type: Full/Partial"
```

## Important Notes

1. **Manual Registration Update**: When refunding, you must also manually update the registration/enrollment status to 'cancelled' or 'inactive'

2. **Audit Trail**: All refunds are logged with:
   - Original payment amount
   - Refund amount
   - Refund type (Full/Partial)
   - Timestamp
   - Stripe refund ID

3. **Revenue Accuracy**: The revenue trend graph now accurately reflects net revenue after refunds

4. **Partial Refunds**: The system supports partial refunds - the difference between total and refund amount is retained as revenue

## Future Enhancements

Potential future improvements:
- Automatic registration/enrollment status updates on refund
- Email notifications to students when refunds are processed
- Refund report/export functionality
- Bulk refund processing for cancelled events
