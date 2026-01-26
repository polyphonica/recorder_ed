"""
Management command to sync Stripe processing fees from Balance Transactions API.

Usage:
    python manage.py sync_stripe_fees --days=7
    python manage.py sync_stripe_fees --start=2024-01-01 --end=2024-01-31
    python manage.py sync_stripe_fees --days=30 --dry-run
    python manage.py sync_stripe_fees --all  # Sync all historical data
"""

import stripe
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.payments.models import StripePayment


class Command(BaseCommand):
    help = 'Sync Stripe processing fees from Balance Transactions API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            help='Number of days to look back (e.g., --days=7)',
        )
        parser.add_argument(
            '--start',
            type=str,
            help='Start date in YYYY-MM-DD format',
        )
        parser.add_argument(
            '--end',
            type=str,
            help='End date in YYYY-MM-DD format',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync all historical transactions (no date filter)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-sync even if stripe_fee is already set',
        )

    def handle(self, *args, **options):
        # Initialize Stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        dry_run = options['dry_run']
        force = options['force']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        # Determine date range
        start_date, end_date = self._get_date_range(options)

        if start_date and end_date:
            self.stdout.write(f'Syncing fees from {start_date} to {end_date}')
        elif options['all']:
            self.stdout.write('Syncing all historical transactions')
        else:
            self.stdout.write(self.style.ERROR(
                'Please specify --days, --start/--end, or --all'
            ))
            return

        # Get payments that need fee data
        payments_queryset = StripePayment.objects.filter(
            status='completed'
        ).exclude(
            stripe_payment_intent_id=''
        ).exclude(
            stripe_payment_intent_id__isnull=True
        )

        if not force:
            # Skip payments that already have fee data
            payments_queryset = payments_queryset.filter(
                stripe_balance_transaction_id__isnull=True
            )

        if start_date:
            payments_queryset = payments_queryset.filter(created_at__gte=start_date)
        if end_date:
            payments_queryset = payments_queryset.filter(created_at__lte=end_date)

        payments = list(payments_queryset)
        total_payments = len(payments)

        self.stdout.write(f'Found {total_payments} payments to process')

        if total_payments == 0:
            self.stdout.write(self.style.SUCCESS('No payments need fee sync'))
            return

        # Build a map of payment_intent_id -> StripePayment
        payment_map = {p.stripe_payment_intent_id: p for p in payments}

        # Fetch balance transactions from Stripe
        updated_count = 0
        skipped_count = 0
        error_count = 0

        try:
            # We'll iterate through balance transactions and match them
            balance_transactions = self._fetch_balance_transactions(start_date, end_date)

            for bt in balance_transactions:
                # Only process charge transactions
                if bt.type != 'charge':
                    continue

                # The source field contains the charge ID, but we need payment_intent
                # We need to get the payment_intent from the charge
                charge_id = bt.source

                try:
                    charge = stripe.Charge.retrieve(charge_id)
                    payment_intent_id = charge.payment_intent

                    if payment_intent_id and payment_intent_id in payment_map:
                        payment = payment_map[payment_intent_id]

                        # Convert fee from cents to pounds
                        fee_amount = Decimal(bt.fee) / Decimal('100')

                        self.stdout.write(
                            f'  {payment_intent_id}: £{payment.total_amount} -> '
                            f'fee £{fee_amount} (bt: {bt.id})'
                        )

                        if not dry_run:
                            payment.stripe_fee = fee_amount
                            payment.stripe_balance_transaction_id = bt.id
                            payment.save(update_fields=[
                                'stripe_fee',
                                'stripe_balance_transaction_id'
                            ])

                        updated_count += 1
                        # Remove from map to track what wasn't matched
                        del payment_map[payment_intent_id]

                except stripe.error.StripeError as e:
                    self.stdout.write(
                        self.style.WARNING(f'  Error fetching charge {charge_id}: {e}')
                    )
                    error_count += 1
                    continue

        except stripe.error.StripeError as e:
            self.stdout.write(
                self.style.ERROR(f'Stripe API error: {e}')
            )
            return

        # Report unmatched payments
        unmatched_count = len(payment_map)

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(f'  Updated: {updated_count}')
        self.stdout.write(f'  Unmatched: {unmatched_count}')
        self.stdout.write(f'  Errors: {error_count}')

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'DRY RUN complete - run without --dry-run to apply changes'
            ))

    def _get_date_range(self, options):
        """Determine start and end dates from command options."""
        start_date = None
        end_date = None

        if options['days']:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=options['days'])
        elif options['start'] and options['end']:
            start_date = timezone.make_aware(
                datetime.strptime(options['start'], '%Y-%m-%d')
            )
            end_date = timezone.make_aware(
                datetime.strptime(options['end'], '%Y-%m-%d')
            )
            # Include the entire end date
            end_date = end_date.replace(hour=23, minute=59, second=59)
        elif options['all']:
            # No date filter
            pass

        return start_date, end_date

    def _fetch_balance_transactions(self, start_date=None, end_date=None):
        """
        Fetch balance transactions from Stripe with pagination.

        Yields balance transaction objects.
        """
        params = {
            'limit': 100,
            'type': 'charge',  # Only get charge transactions
        }

        if start_date:
            params['created'] = {'gte': int(start_date.timestamp())}
        if end_date:
            if 'created' in params:
                params['created']['lte'] = int(end_date.timestamp())
            else:
                params['created'] = {'lte': int(end_date.timestamp())}

        self.stdout.write('Fetching balance transactions from Stripe...')

        has_more = True
        starting_after = None
        total_fetched = 0

        while has_more:
            if starting_after:
                params['starting_after'] = starting_after

            response = stripe.BalanceTransaction.list(**params)

            for bt in response.data:
                total_fetched += 1
                yield bt

            has_more = response.has_more
            if response.data:
                starting_after = response.data[-1].id

        self.stdout.write(f'Fetched {total_fetched} balance transactions')
