"""
Voucher validation and application service.

Handles all business logic for validating vouchers, calculating discounts,
and creating redemption records.
"""
from decimal import Decimal
from typing import Optional, Tuple

import stripe
from django.conf import settings
from django.utils import timezone

from .models import Voucher, VoucherRedemption, StripePayment


class VoucherValidationError(Exception):
    """Custom exception for voucher validation failures with user-friendly messages."""
    pass


class VoucherService:
    """
    Service class for voucher validation, discount calculation, and redemption.

    Usage:
        # Validate a voucher
        voucher = VoucherService.validate_voucher(
            code='SUMMER25',
            student=user,
            domain='private_teaching',
            cart_total=Decimal('50.00')
        )

        # Calculate discount
        discount, final = VoucherService.calculate_discount(voucher, Decimal('50.00'))

        # Create redemption record
        redemption = VoucherService.create_redemption(
            voucher=voucher,
            student=user,
            domain='private_teaching',
            original_amount=Decimal('50.00'),
            discount_amount=discount,
            final_amount=final,
            request=request,
            private_lesson_order=order
        )
    """

    @staticmethod
    def validate_voucher(
        code: str,
        student,
        domain: str,
        cart_total: Decimal,
        workshop=None,
        teacher=None
    ) -> Voucher:
        """
        Validate a voucher code for a specific purchase.

        Args:
            code: The voucher code to validate (case-insensitive)
            student: The User attempting to use the voucher
            domain: 'private_teaching', 'workshops', or 'workshop_series'
            cart_total: Total amount before discount
            workshop: Optional - specific workshop being purchased (for restriction check)
            teacher: Optional - teacher whose products are being purchased

        Returns:
            Voucher object if valid

        Raises:
            VoucherValidationError with user-friendly message
        """
        # Normalize code (uppercase, strip whitespace)
        code = code.strip().upper()

        # 1. Check voucher exists
        try:
            voucher = Voucher.objects.get(code__iexact=code)
        except Voucher.DoesNotExist:
            raise VoucherValidationError("Invalid voucher code. Please check and try again.")

        # 2. Check voucher status is active
        if voucher.status != 'active':
            if voucher.status == 'paused':
                raise VoucherValidationError("This voucher is currently not available.")
            elif voucher.status == 'expired':
                raise VoucherValidationError("This voucher has expired.")
            elif voucher.status == 'exhausted':
                raise VoucherValidationError("This voucher has reached its usage limit.")
            else:
                raise VoucherValidationError("This voucher is not valid.")

        # 3. Check voucher is within valid date range
        now = timezone.now()
        if now < voucher.valid_from:
            raise VoucherValidationError("This voucher is not yet active.")
        if voucher.valid_until and now > voucher.valid_until:
            # Update status and raise error
            voucher.status = 'expired'
            voucher.save(update_fields=['status', 'updated_at'])
            raise VoucherValidationError("This voucher has expired.")

        # 4. Check domain is applicable
        if voucher.applicable_domains and domain not in voucher.applicable_domains:
            domain_names = {
                'private_teaching': 'private lessons',
                'workshops': 'workshops',
                'workshop_series': 'workshop series'
            }
            raise VoucherValidationError(
                f"This voucher cannot be used for {domain_names.get(domain, domain)}."
            )

        # 5. Check student restrictions (if any)
        restricted_students = voucher.restricted_to_students.all()
        if restricted_students.exists():
            if student not in restricted_students:
                raise VoucherValidationError("This voucher is not valid for your account.")

        # 6. Check workshop restrictions (if any)
        if workshop:
            restricted_workshops = voucher.restricted_to_workshops.all()
            if restricted_workshops.exists():
                if workshop not in restricted_workshops:
                    raise VoucherValidationError("This voucher is not valid for this workshop.")

        # 7. Check teacher ownership (voucher must belong to the teacher of the items being purchased)
        if teacher and voucher.created_by != teacher:
            raise VoucherValidationError("This voucher is not valid for this purchase.")

        # 8. Check minimum purchase amount
        if cart_total < voucher.minimum_purchase_amount:
            raise VoucherValidationError(
                f"Minimum purchase of £{voucher.minimum_purchase_amount:.2f} required for this voucher."
            )

        # 9. Check total usage limit
        if voucher.max_uses_total is not None:
            if voucher.times_used >= voucher.max_uses_total:
                voucher.status = 'exhausted'
                voucher.save(update_fields=['status', 'updated_at'])
                raise VoucherValidationError("This voucher has reached its usage limit.")

        # 10. Check per-student usage limit
        student_uses = VoucherRedemption.objects.filter(
            voucher=voucher,
            student=student
        ).count()
        if student_uses >= voucher.max_uses_per_student:
            raise VoucherValidationError("You have already used this voucher.")

        return voucher

    @staticmethod
    def calculate_discount(voucher: Voucher, original_amount: Decimal) -> Tuple[Decimal, Decimal]:
        """
        Calculate the discount and final amount for a voucher.

        Args:
            voucher: The validated Voucher object
            original_amount: The original price before discount

        Returns:
            tuple: (discount_amount, final_amount)

        Note:
            - For 'free' type: discount = original_amount, final = 0
            - For 'percentage': discount = original * (value/100)
            - For 'fixed': discount = min(value, original) - can't exceed original
        """
        original_amount = Decimal(str(original_amount))

        if voucher.discount_type == 'free':
            return original_amount, Decimal('0.00')

        elif voucher.discount_type == 'percentage':
            # Calculate percentage discount
            discount = (original_amount * voucher.discount_value / Decimal('100')).quantize(Decimal('0.01'))
            final = (original_amount - discount).quantize(Decimal('0.01'))
            return discount, max(final, Decimal('0.00'))

        elif voucher.discount_type == 'fixed':
            # Fixed amount discount (can't exceed original price)
            discount = min(voucher.discount_value, original_amount).quantize(Decimal('0.01'))
            final = (original_amount - discount).quantize(Decimal('0.01'))
            return discount, max(final, Decimal('0.00'))

        else:
            # Unknown discount type - no discount
            return Decimal('0.00'), original_amount

    @staticmethod
    def create_redemption(
        voucher: Voucher,
        student,
        domain: str,
        original_amount: Decimal,
        discount_amount: Decimal,
        final_amount: Decimal,
        request=None,
        private_lesson_order=None,
        workshop_registration=None,
        stripe_payment: StripePayment = None
    ) -> VoucherRedemption:
        """
        Create a VoucherRedemption record.

        Args:
            voucher: The Voucher being redeemed
            student: The User redeeming the voucher
            domain: 'private_teaching', 'workshops', or 'workshop_series'
            original_amount: Original price before discount
            discount_amount: Amount discounted
            final_amount: Final price after discount
            request: Optional HttpRequest for IP/user agent tracking
            private_lesson_order: Optional Order for private lessons
            workshop_registration: Optional WorkshopRegistration for workshops
            stripe_payment: Optional StripePayment if payment was made

        Returns:
            VoucherRedemption object
        """
        # Determine if payment was bypassed (100% free)
        payment_bypassed = final_amount == Decimal('0.00')

        # Extract audit info from request
        ip_address = None
        user_agent = ''
        if request:
            ip_address = VoucherService._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Truncate if too long

        redemption = VoucherRedemption.objects.create(
            voucher=voucher,
            student=student,
            domain=domain,
            original_amount=original_amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            payment_bypassed=payment_bypassed,
            private_lesson_order=private_lesson_order,
            workshop_registration=workshop_registration,
            stripe_payment=stripe_payment,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return redemption

    @staticmethod
    def create_or_get_stripe_coupon(voucher: Voucher) -> Optional[str]:
        """
        Create a Stripe coupon for partial discount vouchers, or return existing one.

        For 100% free vouchers, this returns None as Stripe is bypassed entirely.

        Args:
            voucher: The Voucher to create a Stripe coupon for

        Returns:
            Stripe coupon ID string, or None for free vouchers
        """
        # Free vouchers don't need Stripe coupons
        if voucher.discount_type == 'free':
            return None

        # If we already have a Stripe coupon ID, verify it exists and return it
        if voucher.stripe_coupon_id:
            try:
                stripe.Coupon.retrieve(voucher.stripe_coupon_id)
                return voucher.stripe_coupon_id
            except stripe.error.InvalidRequestError:
                # Coupon doesn't exist in Stripe anymore, create new one
                pass

        # Create new Stripe coupon
        coupon_id = f'voucher_{voucher.id}'

        try:
            coupon_params = {
                'id': coupon_id,
                'name': f'Voucher: {voucher.code}',
                'metadata': {
                    'voucher_id': str(voucher.id),
                    'voucher_code': voucher.code
                }
            }

            if voucher.discount_type == 'percentage':
                coupon_params['percent_off'] = float(voucher.discount_value)
            elif voucher.discount_type == 'fixed':
                coupon_params['amount_off'] = int(voucher.discount_value * 100)  # Convert to pence
                coupon_params['currency'] = 'gbp'

            stripe.Coupon.create(**coupon_params)

            # Save the coupon ID to the voucher
            voucher.stripe_coupon_id = coupon_id
            voucher.save(update_fields=['stripe_coupon_id', 'updated_at'])

            return coupon_id

        except stripe.error.InvalidRequestError as e:
            # Coupon might already exist with this ID
            if 'already exists' in str(e).lower():
                voucher.stripe_coupon_id = coupon_id
                voucher.save(update_fields=['stripe_coupon_id', 'updated_at'])
                return coupon_id
            raise

    @staticmethod
    def _get_client_ip(request) -> Optional[str]:
        """Extract client IP from request, handling proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def get_voucher_summary(voucher: Voucher) -> dict:
        """
        Get a summary of voucher for display purposes.

        Args:
            voucher: The Voucher to summarize

        Returns:
            dict with display-friendly voucher information
        """
        discount_display = ''
        if voucher.discount_type == 'free':
            discount_display = '100% Free'
        elif voucher.discount_type == 'percentage':
            discount_display = f'{voucher.discount_value}% off'
        elif voucher.discount_type == 'fixed':
            discount_display = f'£{voucher.discount_value:.2f} off'

        return {
            'code': voucher.code,
            'discount_type': voucher.discount_type,
            'discount_display': discount_display,
            'description': voucher.description,
            'valid_until': voucher.valid_until,
            'uses_remaining': voucher.uses_remaining(),
            'is_usable': voucher.is_usable()
        }
