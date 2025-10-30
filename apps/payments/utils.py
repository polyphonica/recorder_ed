from decimal import Decimal
from django.conf import settings


def calculate_commission(total_amount):
    """
    Calculate platform commission and teacher share
    
    Args:
        total_amount: Total payment amount (Decimal or float)
    
    Returns:
        tuple: (platform_commission, teacher_share)
    """
    total = Decimal(str(total_amount))
    commission_rate = Decimal(str(settings.PLATFORM_COMMISSION_PERCENTAGE)) / Decimal('100')
    
    platform_commission = (total * commission_rate).quantize(Decimal('0.01'))
    teacher_share = total - platform_commission
    
    return platform_commission, teacher_share


def format_stripe_amount(amount):
    """
    Convert amount to Stripe format (smallest currency unit)
    For GBP: £10.50 -> 1050 (pence)
    
    Args:
        amount: Amount in standard currency units (Decimal or float)
    
    Returns:
        int: Amount in smallest currency unit
    """
    return int(Decimal(str(amount)) * 100)


def format_amount_from_stripe(stripe_amount):
    """
    Convert Stripe amount to standard currency format
    For GBP: 1050 (pence) -> £10.50
    
    Args:
        stripe_amount: Amount in smallest currency unit (int)
    
    Returns:
        Decimal: Amount in standard currency units
    """
    return Decimal(stripe_amount) / 100
