import stripe
from django.conf import settings
from django.urls import reverse
from .utils import format_stripe_amount, calculate_commission

# Initialize Stripe with secret key
stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(
    amount,
    student,
    teacher,
    domain,
    success_url,
    cancel_url,
    metadata=None,
    item_name=None,
    item_description=None
):
    """
    Create a Stripe Checkout Session

    Args:
        amount: Payment amount in standard currency (Decimal)
        student: User object (student/customer)
        teacher: User object (teacher/instructor)
        domain: Domain type ('workshops', 'courses', 'private_teaching')
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment is cancelled
        metadata: Additional metadata dict
        item_name: Custom item name (optional, defaults to domain name)
        item_description: Custom item description (optional)

    Returns:
        stripe.checkout.Session object
    """
    # Calculate commission
    platform_commission, teacher_share = calculate_commission(amount)
    
    # Prepare metadata
    session_metadata = {
        'domain': domain,
        'student_id': str(student.id),
        'student_email': student.email,
        'teacher_id': str(teacher.id) if teacher else '',
        'teacher_email': teacher.email if teacher else '',
        'total_amount': str(amount),
        'platform_commission': str(platform_commission),
        'teacher_share': str(teacher_share),
    }
    
    # Add custom metadata
    if metadata:
        session_metadata.update(metadata)
    
    # Create Checkout Session
    try:
        # Use custom item name/description or defaults
        product_name = item_name or f'{domain.replace("_", " ").title()} Payment'
        product_description = item_description or f'Payment for {domain.replace("_", " ")} on RECORDERED'

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'unit_amount': format_stripe_amount(amount),
                    'product_data': {
                        'name': product_name,
                        'description': product_description,
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=student.email,
            metadata=session_metadata,
        )
        return session
    except stripe.error.StripeError as e:
        # Log the error
        print(f"Stripe error: {str(e)}")
        raise


def retrieve_session(session_id):
    """Retrieve a Checkout Session by ID"""
    try:
        return stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e:
        print(f"Error retrieving session: {str(e)}")
        raise


def create_checkout_session_with_items(
    line_items,
    student,
    teacher,
    domain,
    success_url,
    cancel_url,
    metadata=None
):
    """
    Create a Stripe Checkout Session with multiple line items

    Args:
        line_items: List of dicts with 'name', 'description', and 'amount' keys
                    Example: [{'name': 'Workshop 1', 'description': 'Jan 7, 2026', 'amount': Decimal('5.00')}]
        student: User object (student/customer)
        teacher: User object (teacher/instructor) - used for commission calculation
        domain: Domain type ('workshops', 'courses', 'private_teaching')
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment is cancelled
        metadata: Additional metadata dict

    Returns:
        stripe.checkout.Session object
    """
    # Calculate total and commission
    from decimal import Decimal
    total_amount = sum(item['amount'] for item in line_items)
    platform_commission, teacher_share = calculate_commission(total_amount)

    # Prepare metadata
    session_metadata = {
        'domain': domain,
        'student_id': str(student.id),
        'student_email': student.email,
        'teacher_id': str(teacher.id) if teacher else '',
        'teacher_email': teacher.email if teacher else '',
        'total_amount': str(total_amount),
        'platform_commission': str(platform_commission),
        'teacher_share': str(teacher_share),
    }

    # Add custom metadata
    if metadata:
        session_metadata.update(metadata)

    # Build Stripe line items
    stripe_line_items = []
    for item in line_items:
        stripe_line_items.append({
            'price_data': {
                'currency': 'gbp',
                'unit_amount': format_stripe_amount(item['amount']),
                'product_data': {
                    'name': item['name'],
                    'description': item.get('description', ''),
                },
            },
            'quantity': 1,
        })

    # Create Checkout Session
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=stripe_line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=student.email,
            metadata=session_metadata,
        )
        return session
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        raise


def retrieve_payment_intent(payment_intent_id):
    """Retrieve a Payment Intent by ID"""
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        print(f"Error retrieving payment intent: {str(e)}")
        raise


def create_refund(payment_intent_id, amount=None, reason=None, metadata=None):
    """
    Create a refund for a payment

    Args:
        payment_intent_id: Stripe Payment Intent ID
        amount: Refund amount in standard currency (Decimal). If None, full refund.
        reason: Refund reason ('duplicate', 'fraudulent', or 'requested_by_customer')
        metadata: Additional metadata dict

    Returns:
        stripe.Refund object
    """
    try:
        refund_params = {
            'payment_intent': payment_intent_id,
        }

        # Add amount if partial refund
        if amount is not None:
            refund_params['amount'] = format_stripe_amount(amount)

        # Add reason if provided
        if reason:
            refund_params['reason'] = reason

        # Add metadata if provided
        if metadata:
            refund_params['metadata'] = metadata

        # Create the refund
        refund = stripe.Refund.create(**refund_params)
        return refund

    except stripe.error.StripeError as e:
        print(f"Stripe refund error: {str(e)}")
        raise
