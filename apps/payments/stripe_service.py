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
    metadata=None
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
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'unit_amount': format_stripe_amount(amount),
                    'product_data': {
                        'name': f'{domain.replace("_", " ").title()} Payment',
                        'description': f'Payment for {domain.replace("_", " ")} on RECORDERED',
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


def retrieve_payment_intent(payment_intent_id):
    """Retrieve a Payment Intent by ID"""
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        print(f"Error retrieving payment intent: {str(e)}")
        raise
