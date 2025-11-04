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

                    # Create registration
                    registration = WorkshopRegistration.objects.create(
                        session=cart_item.session,
                        student=user,
                        email=user.email,
                        child_profile=cart_item.child_profile,
                        status='registered',
                        payment_status='completed',
                        payment_amount=cart_item.price,
                        stripe_payment_intent_id=stripe_payment.stripe_payment_intent_id,
                        stripe_checkout_session_id=stripe_payment.stripe_checkout_session_id,
                        paid_at=timezone.now(),
                        notes=cart_item.notes if cart_item.notes else ''
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
