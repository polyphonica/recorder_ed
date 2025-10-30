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
        metadata = session.get('metadata', {})
        domain = metadata.get('domain')
        payment_intent_id = session.get('payment_intent')
        
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
        
        # Domain-specific handling
        if domain == 'private_teaching':
            self.handle_private_teaching_payment(metadata, stripe_payment)
        elif domain == 'workshops':
            self.handle_workshop_payment(metadata, stripe_payment)
        elif domain == 'courses':
            self.handle_course_payment(metadata, stripe_payment)
    
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

                # Send payment confirmation email
                if order.student and order.student.email:
                    try:
                        student_name = order.student.get_full_name() or order.student.username
                        subject = f"Payment Confirmation - RECORDERED"

                        email_body = f"Hello {student_name},\n\n"
                        email_body += f"Thank you for your payment! Your order has been confirmed.\n\n"
                        email_body += f"PAYMENT DETAILS:\n"
                        email_body += f"Total Amount: £{order.total_amount:.2f}\n"
                        email_body += f"Payment Date: {order.completed_at.strftime('%d %B %Y at %H:%M')}\n\n"
                        email_body += f"LESSONS PURCHASED:\n"

                        order_items = OrderItem.objects.filter(order=order).select_related('lesson__teacher', 'lesson__subject')
                        for item in order_items:
                            lesson = item.lesson
                            teacher_name = lesson.teacher.get_full_name() if lesson.teacher else "TBA"
                            email_body += f"- {lesson.subject.subject} with {teacher_name}\n"
                            email_body += f"  Date: {lesson.lesson_date.strftime('%d %B %Y')}\n"
                            email_body += f"  Time: {lesson.lesson_time.strftime('%H:%M')}\n"
                            email_body += f"  Price: £{item.price_paid:.2f}\n\n"

                        email_body += f"You can view your lessons at: https://recorder-ed.com/private-teaching/\n\n"
                        email_body += "Best regards,\nRECORDERED Team"

                        send_mail(
                            subject,
                            email_body,
                            settings.DEFAULT_FROM_EMAIL,
                            [order.student.email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        print(f"Error sending payment confirmation email: {e}")

                print(f"Private teaching order {order_id} marked as completed")
            except Order.DoesNotExist:
                print(f"Order {order_id} not found")
    
    def handle_workshop_payment(self, metadata, stripe_payment):
        """Update workshop registration when payment succeeds"""
        from apps.workshops.models import WorkshopRegistration
        from django.core.mail import send_mail
        from django.utils import timezone

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
    
    def handle_course_payment(self, metadata, stripe_payment):
        """Update course enrollment when payment succeeds"""
        from apps.courses.models import Enrollment
        
        enrollment_id = metadata.get('enrollment_id')
        if enrollment_id:
            try:
                enrollment = Enrollment.objects.get(id=enrollment_id)
                enrollment.payment_status = 'confirmed'
                enrollment.stripe_payment_intent_id = stripe_payment.stripe_payment_intent_id
                enrollment.save()
                
                # Update reference in StripePayment
                stripe_payment.course_id = enrollment.course_id
                stripe_payment.save()
                
                print(f"Course enrollment {enrollment_id} confirmed")
            except Enrollment.DoesNotExist:
                print(f"Enrollment {enrollment_id} not found")
