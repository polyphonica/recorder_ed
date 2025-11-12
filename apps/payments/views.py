import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from django.contrib import messages
from decimal import Decimal

from .models import StripePayment
from .stripe_service import retrieve_session, retrieve_payment_intent
from .utils import format_amount_from_stripe


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """Handle Stripe webhook events"""
    
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            # Invalid payload
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return HttpResponse(status=400)
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            self.handle_checkout_session_completed(session)
        
        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            self.handle_payment_intent_succeeded(payment_intent)
        
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            self.handle_payment_failed(payment_intent)
        
        return HttpResponse(status=200)
    
    def handle_checkout_session_completed(self, session):
        """Handle successful checkout session completion"""
        print(f"\n======================================")
        print(f"WEBHOOK: checkout.session.completed")
        print(f"======================================")

        metadata = session.get('metadata', {})
        domain = metadata.get('domain')
        payment_intent_id = session.get('payment_intent')

        print(f"Session ID: {session['id']}")
        print(f"Payment Intent: {payment_intent_id}")
        print(f"Domain: {domain}")
        print(f"Metadata: {metadata}")

        # Create or update StripePayment record
        stripe_payment, created = StripePayment.objects.get_or_create(
            stripe_payment_intent_id=payment_intent_id,
            defaults={
                'stripe_checkout_session_id': session['id'],
                'domain': domain,
                'student_id': metadata.get('student_id'),
                'teacher_id': metadata.get('teacher_id'),
                'total_amount': Decimal(metadata.get('total_amount', '0')),
                'platform_commission': Decimal(metadata.get('platform_commission', '0')),
                'teacher_share': Decimal(metadata.get('teacher_share', '0')),
                'currency': 'gbp',
                'status': 'pending',
                'metadata': metadata,
            }
        )

        print(f"StripePayment created: {created}, ID: {stripe_payment.id}")

        # Domain-specific handling
        if domain == 'private_teaching':
            print(f"→ Routing to PRIVATE TEACHING handler")
            self.handle_private_teaching_payment(metadata, stripe_payment)
        elif domain == 'workshops':
            print(f"→ Routing to WORKSHOPS handler")
            self.handle_workshop_payment(metadata, stripe_payment)
        elif domain == 'courses':
            print(f"→ Routing to COURSES handler")
            self.handle_course_payment(metadata, stripe_payment)
        else:
            print(f"⚠️  WARNING: Unknown domain '{domain}' - no handler called!")

        print(f"======================================\n")
    
    def handle_payment_intent_succeeded(self, payment_intent):
        """Handle successful payment intent"""
        try:
            stripe_payment = StripePayment.objects.get(
                stripe_payment_intent_id=payment_intent['id']
            )
            stripe_payment.mark_completed()
            print(f"Payment completed: {stripe_payment.id}")
        except StripePayment.DoesNotExist:
            print(f"StripePayment not found for payment_intent: {payment_intent['id']}")
    
    def handle_payment_failed(self, payment_intent):
        """Handle failed payment intent"""
        try:
            stripe_payment = StripePayment.objects.get(
                stripe_payment_intent_id=payment_intent['id']
            )
            stripe_payment.mark_failed()
            print(f"Payment failed: {stripe_payment.id}")
        except StripePayment.DoesNotExist:
            print(f"StripePayment not found for failed payment_intent: {payment_intent['id']}")
    
    def handle_private_teaching_payment(self, metadata, stripe_payment):
        """Update private teaching order when payment succeeds"""
        from apps.private_teaching.models import Order, OrderItem
        from lessons.models import Lesson
        from django.core.mail import send_mail
        from django.utils import timezone

        order_id = metadata.get('order_id')
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
                order.payment_status = 'completed'
                order.completed_at = timezone.now()
                order.stripe_payment_intent_id = stripe_payment.stripe_payment_intent_id
                order.save()

                # Update order reference in StripePayment
                stripe_payment.order_id = order_id
                stripe_payment.save()

                # Mark lessons as paid
                lesson_ids = metadata.get('lesson_ids', '').split(',')
                for lesson_id in lesson_ids:
                    if lesson_id:
                        try:
                            # Lesson IDs are UUIDs, not integers - don't convert
                            lesson = Lesson.objects.get(id=lesson_id.strip())
                            lesson.payment_status = 'Paid'
                            lesson.save()
                            print(f"Marked lesson {lesson_id} as Paid")
                        except (Lesson.DoesNotExist, ValueError) as e:
                            print(f"Error updating lesson {lesson_id}: {e}")

                # Send payment confirmation email to student
                try:
                    from apps.private_teaching.notifications import StudentNotificationService
                    StudentNotificationService.send_payment_confirmation(order)
                except Exception as e:
                    print(f"Error sending payment confirmation email: {e}")

                # Send payment notification to teachers
                order_items = OrderItem.objects.filter(order=order).select_related('lesson__teacher')
                teachers = set()
                for item in order_items:
                    if item.lesson.teacher:
                        teachers.add(item.lesson.teacher)

                for teacher in teachers:
                    try:
                        from apps.private_teaching.notifications import TeacherPaymentNotificationService
                        TeacherPaymentNotificationService.send_lesson_payment_notification(order, teacher)
                    except Exception as e:
                        print(f"Error sending teacher payment notification: {e}")

                print(f"Private teaching order {order_id} marked as completed")
            except Order.DoesNotExist:
                print(f"Order {order_id} not found")
    
    def handle_workshop_payment(self, metadata, stripe_payment):
        """Update workshop registration when payment succeeds"""
        from apps.workshops.models import WorkshopRegistration, WorkshopCartItem
        from django.contrib.auth.models import User
        from django.core.mail import send_mail
        from django.utils import timezone

        print(f"\n>>> handle_workshop_payment called")
        print(f"    Metadata keys: {list(metadata.keys())}")

        # Check if this is a cart payment (multiple items)
        cart_item_ids = metadata.get('cart_item_ids')

        if cart_item_ids:
            # CART PAYMENT - Multiple workshops
            print(f"    Detected CART payment with {len(cart_item_ids.split(','))} items")
            self.handle_workshop_cart_payment(metadata, stripe_payment, cart_item_ids)
            return

        # SINGLE REGISTRATION PAYMENT (legacy method)
        print(f"    Detected SINGLE registration payment")
        registration_id = metadata.get('registration_id')
        if registration_id:
            try:
                registration = WorkshopRegistration.objects.select_related(
                    'session__workshop', 'student', 'child_profile'
                ).get(id=registration_id)

                # Update payment status
                registration.payment_status = 'completed'
                registration.status = 'registered'
                registration.paid_at = timezone.now()
                registration.stripe_payment_intent_id = stripe_payment.stripe_payment_intent_id
                registration.save()

                # Update session registration count
                session = registration.session
                session.current_registrations = session.registrations.filter(
                    status__in=['registered', 'promoted', 'attended']
                ).count()
                session.save(update_fields=['current_registrations'])

                # Send notification to instructor
                try:
                    from apps.workshops.notifications import InstructorNotificationService
                    InstructorNotificationService.send_new_registration_notification(registration)
                except Exception as e:
                    print(f"Failed to send instructor notification: {e}")

                # Update workshop total registrations if needed
                workshop = session.workshop
                workshop.total_registrations = WorkshopRegistration.objects.filter(
                    session__workshop=workshop,
                    status__in=['registered', 'attended']
                ).count()
                workshop.save(update_fields=['total_registrations'])

                # Update reference in StripePayment
                stripe_payment.workshop_id = workshop.id
                stripe_payment.save()

                # Send confirmation email
                if registration.student and registration.student.email:
                    try:
                        student_name = registration.student_name  # Uses property for child or adult
                        guardian_email = registration.email or registration.student.email

                        subject = f"Workshop Registration Confirmed - {workshop.title}"

                        email_body = f"Hello {registration.student.get_full_name() or registration.student.username},\n\n"

                        if registration.child_profile:
                            email_body += f"Thank you for registering {student_name} for the workshop!\n\n"
                        else:
                            email_body += f"Thank you for registering for the workshop!\n\n"

                        email_body += f"WORKSHOP DETAILS:\n"
                        email_body += f"Workshop: {workshop.title}\n"
                        email_body += f"Date: {session.start_datetime.strftime('%A, %d %B %Y')}\n"
                        email_body += f"Time: {session.start_datetime.strftime('%H:%M')} - {session.end_datetime.strftime('%H:%M')}\n"

                        if workshop.delivery_method == 'online':
                            email_body += f"Delivery: Online\n"
                            if session.meeting_url:
                                email_body += f"Meeting Link: {session.meeting_url}\n"
                        elif workshop.delivery_method == 'in_person':
                            email_body += f"Delivery: In-Person\n"
                            if workshop.venue_name:
                                email_body += f"Venue: {workshop.venue_name}\n"
                            if workshop.full_venue_address:
                                email_body += f"Address: {workshop.full_venue_address}\n"

                        email_body += f"\nAmount Paid: £{registration.payment_amount:.2f}\n"
                        email_body += f"Payment Date: {registration.paid_at.strftime('%d %B %Y at %H:%M')}\n\n"

                        email_body += f"You can view your registration details at: https://www.recorder-ed.com/workshops/registration/{registration.id}/confirm/\n\n"
                        email_body += "Best regards,\nRECORDERED Team"

                        send_mail(
                            subject,
                            email_body,
                            settings.DEFAULT_FROM_EMAIL,
                            [guardian_email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        print(f"Error sending workshop confirmation email: {e}")

                print(f"Workshop registration {registration_id} confirmed and email sent")
            except WorkshopRegistration.DoesNotExist:
                print(f"WorkshopRegistration {registration_id} not found")

    def handle_workshop_cart_payment(self, metadata, stripe_payment, cart_item_ids):
        """Handle cart-based workshop payment (multiple sessions)"""
        from apps.workshops.models import WorkshopRegistration, WorkshopCartItem
        from django.contrib.auth.models import User
        from django.core.mail import send_mail
        from django.utils import timezone

        print(f"\n=== WORKSHOP CART PAYMENT WEBHOOK ===")
        print(f"Metadata: {metadata}")
        print(f"Cart Item IDs: {cart_item_ids}")
        print(f"Stripe Payment ID: {stripe_payment.stripe_payment_intent_id}")

        item_ids = [id.strip() for id in cart_item_ids.split(',')]
        user_id = metadata.get('student_id')

        print(f"Processing {len(item_ids)} cart items for user {user_id}")

        try:
            user = User.objects.get(id=user_id)
            print(f"Found user: {user.username} ({user.email})")
            created_registrations = []

            for item_id in item_ids:
                print(f"\n  Processing cart item: {item_id}")
                try:
                    cart_item = WorkshopCartItem.objects.select_related(
                        'session__workshop__instructor',
                        'session__workshop__category',
                        'child_profile'
                    ).get(id=item_id)

                    print(f"  Found cart item: {cart_item.session.workshop.title}")
                    print(f"  Session: {cart_item.session.start_datetime}")
                    print(f"  Price: £{cart_item.price}")

                    # Create registration with data from cart item
                    registration = WorkshopRegistration.objects.create(
                        session=cart_item.session,
                        student=user,
                        email=cart_item.email or user.email,
                        phone=cart_item.phone or '',
                        emergency_contact=cart_item.emergency_contact or '',
                        experience_level=cart_item.experience_level or '',
                        expectations=cart_item.expectations or '',
                        special_requirements=cart_item.special_requirements or '',
                        child_profile=cart_item.child_profile,
                        status='registered',
                        payment_status='completed',
                        payment_amount=cart_item.price,
                        stripe_payment_intent_id=stripe_payment.stripe_payment_intent_id,
                        stripe_checkout_session_id=stripe_payment.stripe_checkout_session_id,
                        paid_at=timezone.now()
                    )

                    print(f"  ✓ Created registration ID: {registration.id}")
                    print(f"    - Status: {registration.status}")
                    print(f"    - Payment Status: {registration.payment_status}")
                    print(f"    - Paid At: {registration.paid_at}")
                    print(f"    - Registration Date: {registration.registration_date}")

                    # Update session registration count
                    session = cart_item.session
                    session.current_registrations = session.registrations.filter(
                        status__in=['registered', 'promoted', 'attended']
                    ).count()
                    session.save(update_fields=['current_registrations'])

                    # Update workshop total registrations
                    workshop = session.workshop
                    workshop.total_registrations = WorkshopRegistration.objects.filter(
                        session__workshop=workshop,
                        status__in=['registered', 'attended']
                    ).count()
                    workshop.save(update_fields=['total_registrations'])

                    # Send notification to instructor
                    try:
                        from apps.workshops.notifications import InstructorNotificationService
                        InstructorNotificationService.send_new_registration_notification(registration)
                        print(f"  ✓ Sent notification to instructor {session.workshop.instructor.email}")
                    except Exception as e:
                        print(f"  ✗ Failed to send instructor notification: {e}")

                    # Store for email
                    created_registrations.append(registration)

                    # Delete cart item
                    cart_item.delete()
                    print(f"  ✓ Deleted cart item {item_id}")

                except WorkshopCartItem.DoesNotExist:
                    print(f"  ✗ Cart item {item_id} not found (may have been already processed)")
                except Exception as e:
                    import traceback
                    print(f"  ✗ Error processing cart item {item_id}: {str(e)}")
                    print(f"  Traceback: {traceback.format_exc()}")

            # Send consolidated confirmation email
            if created_registrations and user.email:
                try:
                    print(f"\nSending confirmation email to {user.email}...")
                    self.send_workshop_cart_confirmation_email(user, created_registrations, stripe_payment)
                    print(f"✓ Email sent successfully")
                except Exception as e:
                    print(f"✗ Error sending cart confirmation email: {e}")

            print(f"\n=== SUMMARY ===")
            print(f"Successfully created {len(created_registrations)} registrations:")
            for reg in created_registrations:
                print(f"  - {reg.session.workshop.title} (ID: {reg.id}, Status: {reg.status}, Payment: {reg.payment_status})")

            # Mark payment as completed
            stripe_payment.mark_completed()
            print(f"✓ Marked StripePayment {stripe_payment.id} as completed")
            print(f"=== END WORKSHOP CART PAYMENT ===\n")

        except User.DoesNotExist:
            print(f"✗ User {user_id} not found")
        except Exception as e:
            import traceback
            print(f"✗ Error in handle_workshop_cart_payment: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")

    def send_workshop_cart_confirmation_email(self, user, registrations, stripe_payment):
        """Send confirmation email for cart-based workshop purchase"""
        from django.core.mail import send_mail
        from django.conf import settings

        total_amount = stripe_payment.total_amount
        user_name = user.get_full_name() or user.username

        subject = f"Workshop Registration Confirmed - {len(registrations)} Session{'s' if len(registrations) > 1 else ''}"

        email_body = f"Hello {user_name},\n\n"
        email_body += f"Thank you for your payment! Your workshop registration{'s are' if len(registrations) > 1 else ' is'} confirmed.\n\n"
        email_body += f"PAYMENT DETAILS:\n"
        email_body += f"Total Amount: £{total_amount:.2f}\n"
        email_body += f"Payment Date: {registrations[0].paid_at.strftime('%d %B %Y at %H:%M')}\n\n"
        email_body += f"WORKSHOPS REGISTERED:\n\n"

        for reg in registrations:
            workshop = reg.session.workshop
            session = reg.session

            participant_name = reg.student_name  # Uses property for child or adult

            if reg.child_profile:
                email_body += f"Workshop: {workshop.title} (for {participant_name})\n"
            else:
                email_body += f"Workshop: {workshop.title}\n"

            email_body += f"Date: {session.start_datetime.strftime('%A, %d %B %Y')}\n"
            email_body += f"Time: {session.start_datetime.strftime('%H:%M')} - {session.end_datetime.strftime('%H:%M')}\n"

            if workshop.delivery_method == 'online':
                email_body += f"Delivery: Online\n"
                if session.meeting_url:
                    email_body += f"Meeting Link: {session.meeting_url}\n"
            else:
                email_body += f"Delivery: In-Person\n"
                if workshop.venue_name:
                    email_body += f"Venue: {workshop.venue_name}\n"
                if workshop.full_venue_address:
                    email_body += f"Address: {workshop.full_venue_address}\n"

            email_body += f"Price: £{reg.payment_amount:.2f}\n\n"

        email_body += f"You can view your registrations at: https://www.recorder-ed.com/workshops/my/registrations/\n\n"
        email_body += "Best regards,\nRECORDERED Team"

        send_mail(
            subject,
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )

    def handle_course_payment(self, metadata, stripe_payment):
        """Update course enrollment when payment succeeds"""
        from apps.courses.models import CourseEnrollment
        from django.core.mail import send_mail
        from django.utils import timezone

        enrollment_id = metadata.get('enrollment_id')
        if enrollment_id:
            try:
                enrollment = CourseEnrollment.objects.select_related(
                    'course', 'student', 'child_profile'
                ).get(id=enrollment_id)

                # Update payment status
                enrollment.payment_status = 'completed'
                enrollment.paid_at = timezone.now()
                enrollment.stripe_payment_intent_id = stripe_payment.stripe_payment_intent_id
                enrollment.save()

                # Update course enrollment count
                course = enrollment.course
                course.total_enrollments = CourseEnrollment.objects.filter(
                    course=course,
                    is_active=True,
                    payment_status__in=['completed', 'not_required']
                ).count()
                course.save(update_fields=['total_enrollments'])

                # Update reference in StripePayment
                stripe_payment.course_id = course.id
                stripe_payment.save()

                # Send notification to instructor
                try:
                    from apps.courses.notifications import InstructorNotificationService
                    InstructorNotificationService.send_new_enrollment_notification(enrollment)
                except Exception as e:
                    print(f"Failed to send instructor notification: {e}")

                # Send confirmation email
                if enrollment.student and enrollment.student.email:
                    try:
                        student_name = enrollment.child_profile.full_name if enrollment.child_profile else (enrollment.student.get_full_name() or enrollment.student.username)
                        guardian_email = enrollment.student.email

                        subject = f"Course Enrollment Confirmed - {course.title}"

                        email_body = f"Hello {enrollment.student.get_full_name() or enrollment.student.username},\n\n"

                        if enrollment.child_profile:
                            email_body += f"Thank you for enrolling {student_name} in the course!\n\n"
                        else:
                            email_body += f"Thank you for enrolling in the course!\n\n"

                        email_body += f"COURSE DETAILS:\n"
                        email_body += f"Course: {course.title}\n"
                        email_body += f"Grade Level: {course.get_grade_display()}\n"
                        email_body += f"Instructor: {course.instructor.get_full_name() or course.instructor.username}\n"
                        email_body += f"\nAmount Paid: £{enrollment.payment_amount:.2f}\n"
                        email_body += f"Payment Date: {enrollment.paid_at.strftime('%d %B %Y at %H:%M')}\n\n"

                        email_body += f"You can access your course at: https://www.recorder-ed.com/courses/{course.slug}/\n\n"
                        email_body += "Best regards,\nRECORDERED Team"

                        send_mail(
                            subject,
                            email_body,
                            settings.DEFAULT_FROM_EMAIL,
                            [guardian_email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        print(f"Error sending course confirmation email: {e}")

                print(f"Course enrollment {enrollment_id} confirmed and email sent")
            except CourseEnrollment.DoesNotExist:
                print(f"CourseEnrollment {enrollment_id} not found")


# ============================================================================
# FINANCE DASHBOARD VIEWS
# ============================================================================

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from .finance_service import FinanceService


class TeacherOnlyMixin(UserPassesTestMixin):
    """Mixin to ensure only teachers can access finance views"""

    def test_func(self):
        return (
            self.request.user.is_authenticated and
            (self.request.user.profile.is_teacher or self.request.user.is_staff)
        )

    def handle_no_permission(self):
        messages.error(self.request, 'You must be a teacher to access finance dashboard.')
        return redirect('core:home')


class FinanceDashboardView(LoginRequiredMixin, TeacherOnlyMixin, TemplateView):
    """
    Unified finance dashboard showing revenue from all domains.
    Single source of truth for teacher's financial data.
    """
    template_name = 'payments/finance_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user

        # Get date range from query params (default to last 30 days)
        date_range = self.request.GET.get('range', '30')

        if date_range == 'all':
            start_date = None
            end_date = None
        elif date_range == '7':
            start_date = timezone.now() - timedelta(days=7)
            end_date = None
        elif date_range == '30':
            start_date = timezone.now() - timedelta(days=30)
            end_date = None
        elif date_range == '90':
            start_date = timezone.now() - timedelta(days=90)
            end_date = None
        elif date_range == 'year':
            start_date = timezone.now() - timedelta(days=365)
            end_date = None
        else:
            start_date = timezone.now() - timedelta(days=30)
            end_date = None

        # Get overall summary
        summary = FinanceService.get_teacher_revenue_summary(teacher, start_date, end_date)

        # Get recent transactions
        recent_transactions = FinanceService.get_recent_transactions(teacher, limit=10)

        # Get revenue trend
        trend = FinanceService.get_revenue_trend(teacher, days=30)

        # Get expense data
        from apps.expenses.models import Expense
        expense_queryset = Expense.objects.filter(created_by=teacher)

        if start_date:
            expense_queryset = expense_queryset.filter(date__gte=start_date.date())

        # Calculate total expenses
        total_expenses = expense_queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Calculate expenses by business area
        expenses_by_area = expense_queryset.values('business_area').annotate(
            total=Sum('amount')
        ).order_by('business_area')

        expense_breakdown = {
            'workshops': Decimal('0.00'),
            'courses': Decimal('0.00'),
            'private_teaching': Decimal('0.00'),
            'general': Decimal('0.00'),
        }

        for item in expenses_by_area:
            expense_breakdown[item['business_area']] = item['total']

        # Calculate net profit
        net_profit = summary['total_revenue'] - total_expenses

        # Add expense count
        expense_count = expense_queryset.count()

        context.update({
            'summary': summary,
            'recent_transactions': recent_transactions,
            'trend': trend,
            'selected_range': date_range,
            'total_expenses': total_expenses,
            'expense_breakdown': expense_breakdown,
            'net_profit': net_profit,
            'expense_count': expense_count,
        })

        return context


class WorkshopRevenueView(LoginRequiredMixin, TeacherOnlyMixin, TemplateView):
    """Detailed workshop revenue breakdown"""
    template_name = 'payments/workshop_revenue.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user

        # Get date range
        date_range = self.request.GET.get('range', '30')
        if date_range == 'all':
            start_date = None
            end_date = None
        elif date_range == '7':
            start_date = timezone.now() - timedelta(days=7)
            end_date = None
        elif date_range == '30':
            start_date = timezone.now() - timedelta(days=30)
            end_date = None
        elif date_range == '90':
            start_date = timezone.now() - timedelta(days=90)
            end_date = None
        else:
            start_date = timezone.now() - timedelta(days=30)
            end_date = None

        # Get domain revenue
        domain_data = FinanceService.get_domain_revenue(teacher, 'workshops', start_date, end_date)

        # Get workshop breakdown
        workshop_breakdown = FinanceService.get_workshop_revenue_breakdown(teacher, start_date, end_date)

        # Get workshop expenses
        from apps.expenses.models import Expense
        workshop_expenses = Expense.objects.filter(
            created_by=teacher,
            business_area='workshops'
        )
        if start_date:
            workshop_expenses = workshop_expenses.filter(date__gte=start_date.date())

        total_expenses = workshop_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        net_profit = domain_data['total_revenue'] - total_expenses

        context.update({
            'domain_data': domain_data,
            'workshop_breakdown': workshop_breakdown,
            'selected_range': date_range,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
        })

        return context


class CourseRevenueView(LoginRequiredMixin, TeacherOnlyMixin, TemplateView):
    """Detailed course revenue breakdown"""
    template_name = 'payments/course_revenue.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user

        # Get date range
        date_range = self.request.GET.get('range', '30')
        if date_range == 'all':
            start_date = None
            end_date = None
        elif date_range == '7':
            start_date = timezone.now() - timedelta(days=7)
            end_date = None
        elif date_range == '30':
            start_date = timezone.now() - timedelta(days=30)
            end_date = None
        elif date_range == '90':
            start_date = timezone.now() - timedelta(days=90)
            end_date = None
        else:
            start_date = timezone.now() - timedelta(days=30)
            end_date = None

        # Get domain revenue
        domain_data = FinanceService.get_domain_revenue(teacher, 'courses', start_date, end_date)

        # Get course breakdown
        course_breakdown = FinanceService.get_course_revenue_breakdown(teacher, start_date, end_date)

        # Get course expenses
        from apps.expenses.models import Expense
        course_expenses = Expense.objects.filter(
            created_by=teacher,
            business_area='courses'
        )
        if start_date:
            course_expenses = course_expenses.filter(date__gte=start_date.date())

        total_expenses = course_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        net_profit = domain_data['total_revenue'] - total_expenses

        context.update({
            'domain_data': domain_data,
            'course_breakdown': course_breakdown,
            'selected_range': date_range,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
        })

        return context


class PrivateTeachingRevenueView(LoginRequiredMixin, TeacherOnlyMixin, TemplateView):
    """Detailed private teaching revenue breakdown"""
    template_name = 'payments/private_teaching_revenue.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user

        # Get date range
        date_range = self.request.GET.get('range', '30')
        if date_range == 'all':
            start_date = None
            end_date = None
        elif date_range == '7':
            start_date = timezone.now() - timedelta(days=7)
            end_date = None
        elif date_range == '30':
            start_date = timezone.now() - timedelta(days=30)
            end_date = None
        elif date_range == '90':
            start_date = timezone.now() - timedelta(days=90)
            end_date = None
        else:
            start_date = timezone.now() - timedelta(days=30)
            end_date = None

        # Get domain revenue
        domain_data = FinanceService.get_domain_revenue(teacher, 'private_teaching', start_date, end_date)

        # Get student breakdown
        student_breakdown = FinanceService.get_private_teaching_revenue_breakdown(teacher, start_date, end_date)

        # Get private teaching expenses
        from apps.expenses.models import Expense
        private_teaching_expenses = Expense.objects.filter(
            created_by=teacher,
            business_area='private_teaching'
        )
        if start_date:
            private_teaching_expenses = private_teaching_expenses.filter(date__gte=start_date.date())

        total_expenses = private_teaching_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        net_profit = domain_data['total_revenue'] - total_expenses

        context.update({
            'domain_data': domain_data,
            'student_breakdown': student_breakdown,
            'selected_range': date_range,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
        })

        return context


class PrivateTeachingSubjectRevenueView(LoginRequiredMixin, TeacherOnlyMixin, TemplateView):
    """Detailed private teaching revenue breakdown by subject"""
    template_name = 'payments/private_teaching_subject_revenue.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user

        # Get date range
        date_range = self.request.GET.get('range', '30')
        if date_range == 'all':
            start_date = None
            end_date = None
        elif date_range == '7':
            start_date = timezone.now() - timedelta(days=7)
            end_date = None
        elif date_range == '30':
            start_date = timezone.now() - timedelta(days=30)
            end_date = None
        elif date_range == '90':
            start_date = timezone.now() - timedelta(days=90)
            end_date = None
        else:
            start_date = timezone.now() - timedelta(days=30)
            end_date = None

        # Get domain revenue
        domain_data = FinanceService.get_domain_revenue(teacher, 'private_teaching', start_date, end_date)

        # Get subject breakdown
        subject_breakdown = FinanceService.get_private_teaching_subject_breakdown(teacher, start_date, end_date)

        # Get private teaching expenses
        from apps.expenses.models import Expense
        private_teaching_expenses = Expense.objects.filter(
            created_by=teacher,
            business_area='private_teaching'
        )
        if start_date:
            private_teaching_expenses = private_teaching_expenses.filter(date__gte=start_date.date())

        total_expenses = private_teaching_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        net_profit = domain_data['total_revenue'] - total_expenses

        context.update({
            'domain_data': domain_data,
            'subject_breakdown': subject_breakdown,
            'selected_range': date_range,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
        })

        return context


class ProfitLossView(LoginRequiredMixin, TeacherOnlyMixin, TemplateView):
    """
    Profit & Loss statement showing revenue vs expenses by business area.
    Provides complete financial picture with net profit calculations.
    """
    template_name = 'payments/profit_loss.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user

        # Check for custom date range first
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')

        if start_date_str and end_date_str:
            # Custom date range provided
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            start_date = timezone.make_aware(start_date)
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = timezone.make_aware(end_date.replace(hour=23, minute=59, second=59))
            date_range = 'custom'
        else:
            # Use quick select range
            date_range = self.request.GET.get('range', 'tax_year')

            if date_range == 'all':
                start_date = None
                end_date = None
                start_date_str = ''
                end_date_str = ''
            elif date_range == '7':
                start_date = timezone.now() - timedelta(days=7)
                end_date = timezone.now()
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')
            elif date_range == '30':
                start_date = timezone.now() - timedelta(days=30)
                end_date = timezone.now()
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')
            elif date_range == '90':
                start_date = timezone.now() - timedelta(days=90)
                end_date = timezone.now()
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')
            elif date_range == 'year':
                start_date = timezone.now() - timedelta(days=365)
                end_date = timezone.now()
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')
            elif date_range == 'tax_year':
                # UK tax year: April 6 to April 5
                from datetime import date
                today = timezone.now().date()
                current_year = today.year

                # Determine current tax year
                if today >= date(current_year, 4, 6):
                    # After April 6 - tax year is April 6 current_year to April 5 next_year
                    tax_year_start = date(current_year, 4, 6)
                    tax_year_end = date(current_year + 1, 4, 5)
                else:
                    # Before April 6 - tax year is April 6 last_year to April 5 current_year
                    tax_year_start = date(current_year - 1, 4, 6)
                    tax_year_end = date(current_year, 4, 5)

                start_date = timezone.make_aware(timezone.datetime.combine(tax_year_start, timezone.datetime.min.time()))
                end_date = timezone.make_aware(timezone.datetime.combine(tax_year_end, timezone.datetime.max.time()))
                start_date_str = tax_year_start.strftime('%Y-%m-%d')
                end_date_str = tax_year_end.strftime('%Y-%m-%d')
            else:
                # Default to current tax year
                from datetime import date
                today = timezone.now().date()
                current_year = today.year

                if today >= date(current_year, 4, 6):
                    tax_year_start = date(current_year, 4, 6)
                    tax_year_end = date(current_year + 1, 4, 5)
                else:
                    tax_year_start = date(current_year - 1, 4, 6)
                    tax_year_end = date(current_year, 4, 5)

                start_date = timezone.make_aware(timezone.datetime.combine(tax_year_start, timezone.datetime.min.time()))
                end_date = timezone.make_aware(timezone.datetime.combine(tax_year_end, timezone.datetime.max.time()))
                start_date_str = tax_year_start.strftime('%Y-%m-%d')
                end_date_str = tax_year_end.strftime('%Y-%m-%d')

        # Get revenue summary
        summary = FinanceService.get_teacher_revenue_summary(teacher, start_date, end_date)

        # Get expense data
        from apps.expenses.models import Expense
        expense_queryset = Expense.objects.filter(created_by=teacher)

        if start_date:
            expense_queryset = expense_queryset.filter(date__gte=start_date.date())

        # Calculate total expenses
        total_expenses = expense_queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Calculate expenses by business area
        expenses_by_area = expense_queryset.values('business_area').annotate(
            total=Sum('amount')
        ).order_by('business_area')

        expense_breakdown = {
            'workshops': Decimal('0.00'),
            'courses': Decimal('0.00'),
            'private_teaching': Decimal('0.00'),
            'general': Decimal('0.00'),
        }

        for item in expenses_by_area:
            expense_breakdown[item['business_area']] = item['total']

        # Calculate net profit by business area
        profit_by_area = {
            'workshops': {
                'revenue': summary['by_domain']['workshops']['revenue'],
                'expenses': expense_breakdown['workshops'],
                'net_profit': summary['by_domain']['workshops']['revenue'] - expense_breakdown['workshops'],
            },
            'courses': {
                'revenue': summary['by_domain']['courses']['revenue'],
                'expenses': expense_breakdown['courses'],
                'net_profit': summary['by_domain']['courses']['revenue'] - expense_breakdown['courses'],
            },
            'private_teaching': {
                'revenue': summary['by_domain']['private_teaching']['revenue'],
                'expenses': expense_breakdown['private_teaching'],
                'net_profit': summary['by_domain']['private_teaching']['revenue'] - expense_breakdown['private_teaching'],
            },
            'general': {
                'revenue': Decimal('0.00'),  # General doesn't have revenue
                'expenses': expense_breakdown['general'],
                'net_profit': -expense_breakdown['general'],  # General is always a cost
            },
        }

        # Calculate overall net profit
        net_profit = summary['total_revenue'] - total_expenses

        # Get monthly trend data (last 12 months)
        from django.db.models.functions import TruncMonth
        from dateutil.relativedelta import relativedelta

        twelve_months_ago = timezone.now() - relativedelta(months=12)

        # Monthly revenue trend
        revenue_trend = FinanceService.get_revenue_trend(teacher, days=365)

        # Monthly expense trend
        monthly_expenses = expense_queryset.filter(
            date__gte=twelve_months_ago.date()
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')

        context.update({
            'summary': summary,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'profit_by_area': profit_by_area,
            'expense_breakdown': expense_breakdown,
            'revenue_trend': revenue_trend,
            'monthly_expenses': monthly_expenses,
            'selected_range': date_range,
            'start_date_str': start_date_str,
            'end_date_str': end_date_str,
        })

        return context



class ProfitLossCSVExportView(LoginRequiredMixin, TeacherOnlyMixin, View):
    """
    Export Profit & Loss statement as CSV file for tax/accounting purposes.
    """

    def get(self, request):
        import csv
        from datetime import datetime

        teacher = request.user

        # Get date range
        start_date_str = request.GET.get("start_date", "")
        end_date_str = request.GET.get("end_date", "")

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            start_date = timezone.make_aware(start_date)
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            end_date = timezone.make_aware(end_date.replace(hour=23, minute=59, second=59))
        else:
            # Default to current UK tax year
            from datetime import date
            today = timezone.now().date()
            current_year = today.year

            if today >= date(current_year, 4, 6):
                tax_year_start = date(current_year, 4, 6)
                tax_year_end = date(current_year + 1, 4, 5)
            else:
                tax_year_start = date(current_year - 1, 4, 6)
                tax_year_end = date(current_year, 4, 5)

            start_date = timezone.make_aware(timezone.datetime.combine(tax_year_start, timezone.datetime.min.time()))
            end_date = timezone.make_aware(timezone.datetime.combine(tax_year_end, timezone.datetime.max.time()))
            start_date_str = tax_year_start.strftime("%Y-%m-%d")
            end_date_str = tax_year_end.strftime("%Y-%m-%d")

        # Get revenue summary
        summary = FinanceService.get_teacher_revenue_summary(teacher, start_date, end_date)

        # Get expense data
        from apps.expenses.models import Expense
        expense_queryset = Expense.objects.filter(created_by=teacher)

        if start_date:
            expense_queryset = expense_queryset.filter(date__gte=start_date.date())
        if end_date:
            expense_queryset = expense_queryset.filter(date__lte=end_date.date())

        total_expenses = expense_queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Calculate expenses by business area
        expenses_by_area = expense_queryset.values("business_area").annotate(
            total=Sum("amount")
        ).order_by("business_area")

        expense_breakdown = {
            "workshops": Decimal("0.00"),
            "courses": Decimal("0.00"),
            "private_teaching": Decimal("0.00"),
            "general": Decimal("0.00"),
        }

        for item in expenses_by_area:
            expense_breakdown[item["business_area"]] = item["total"]

        # Calculate net profit by business area
        profit_by_area = {
            "workshops": {
                "revenue": summary["by_domain"]["workshops"]["revenue"],
                "expenses": expense_breakdown["workshops"],
                "net_profit": summary["by_domain"]["workshops"]["revenue"] - expense_breakdown["workshops"],
            },
            "courses": {
                "revenue": summary["by_domain"]["courses"]["revenue"],
                "expenses": expense_breakdown["courses"],
                "net_profit": summary["by_domain"]["courses"]["revenue"] - expense_breakdown["courses"],
            },
            "private_teaching": {
                "revenue": summary["by_domain"]["private_teaching"]["revenue"],
                "expenses": expense_breakdown["private_teaching"],
                "net_profit": summary["by_domain"]["private_teaching"]["revenue"] - expense_breakdown["private_teaching"],
            },
            "general": {
                "revenue": Decimal("0.00"),
                "expenses": expense_breakdown["general"],
                "net_profit": -expense_breakdown["general"],
            },
        }

        net_profit = summary["total_revenue"] - total_expenses

        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        filename = f"profit_loss_{start_date_str}_to_{end_date_str}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # Header
        writer.writerow(["Profit & Loss Statement"])
        writer.writerow([f"Period: {start_date_str} to {end_date_str}"])
        writer.writerow([f"Teacher: {teacher.get_full_name()}"])
        writer.writerow([f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}"])
        writer.writerow([])  # Empty row

        # Column headers
        writer.writerow(["Business Area", "Revenue (£)", "Expenses (£)", "Net Profit (£)", "Profit Margin (%)"])

        # Data rows
        for area_key, area_name in [
            ("workshops", "Workshops"),
            ("courses", "Courses"),
            ("private_teaching", "Private Teaching"),
            ("general", "General/Shared"),
        ]:
            area_data = profit_by_area[area_key]
            revenue = float(area_data["revenue"])
            expenses = float(area_data["expenses"])
            net_profit_val = float(area_data["net_profit"])

            if revenue > 0:
                profit_margin = (net_profit_val / revenue) * 100
            else:
                profit_margin = 0

            writer.writerow([
                area_name,
                f"{revenue:.2f}",
                f"{expenses:.2f}",
                f"{net_profit_val:.2f}",
                f"{profit_margin:.1f}" if revenue > 0 else "-"
            ])

        # Total row
        writer.writerow([])  # Empty row
        writer.writerow([
            "TOTAL",
            f'{float(summary["total_revenue"]):.2f}',
            f"{float(total_expenses):.2f}",
            f"{float(net_profit):.2f}",
            f'{(float(net_profit) / float(summary["total_revenue"]) * 100):.1f}' if summary["total_revenue"] > 0 else "-"
        ])

        # Additional info
        writer.writerow([])
        writer.writerow([])
        writer.writerow(["Additional Information"])
        writer.writerow(["Gross Revenue", f'£{float(summary["total_gross"]):.2f}'])
        writer.writerow(["Platform Fee (10%)", f'£{float(summary["total_commission"]):.2f}'])
        writer.writerow(["Net Revenue", f'£{float(summary["total_revenue"]):.2f}'])
        writer.writerow(["Total Expenses", f"£{float(total_expenses):.2f}"])
        writer.writerow(["Net Profit", f"£{float(net_profit):.2f}"])

        return response

