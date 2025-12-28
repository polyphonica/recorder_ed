from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse


def send_purchase_confirmation(purchase):
    """
    Send purchase confirmation email with download links.

    Args:
        purchase: ProductPurchase instance
    """
    product = purchase.product
    student = purchase.student

    # Build download links (files and URLs)
    download_links = []
    for file in product.main_files:
        link_data = {
            'title': file.title,
            'is_file': file.is_file,
            'is_url': file.is_url,
        }

        # Add file download link if it's a file
        if file.is_file:
            link_data['file_url'] = f"{settings.SITE_URL}{reverse('digital_products:download_file', kwargs={'purchase_id': purchase.id, 'file_id': file.id})}"
            link_data['file_size'] = file.file_size

        # Add URL access link if it's a URL
        if file.is_url:
            link_data['content_url'] = f"{settings.SITE_URL}{reverse('digital_products:access_url', kwargs={'purchase_id': purchase.id, 'file_id': file.id})}"
            link_data['is_video'] = file.is_video_url

        download_links.append(link_data)

    context = {
        'student': student,
        'product': product,
        'purchase': purchase,
        'download_links': download_links,
        'site_name': getattr(settings, 'SITE_NAME', 'RecorderEd'),
        'site_url': settings.SITE_URL,
        'my_purchases_url': f"{settings.SITE_URL}{reverse('digital_products:my_purchases')}"
    }

    # Render email
    subject = f"Download Your Purchase: {product.title}"
    html_message = render_to_string('digital_products/emails/purchase_confirmation.html', context)
    plain_message = render_to_string('digital_products/emails/purchase_confirmation.txt', context)

    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[student.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_cart_purchase_confirmation(student, purchases):
    """
    Send consolidated purchase confirmation email for cart checkout.

    Args:
        student: User instance
        purchases: List of ProductPurchase instances
    """
    # Build product list with download links
    products_data = []
    for purchase in purchases:
        product = purchase.product
        download_links = []

        for file in product.main_files:
            link_data = {
                'title': file.title,
                'is_file': file.is_file,
                'is_url': file.is_url,
            }

            # Add file download link if it's a file
            if file.is_file:
                link_data['file_url'] = f"{settings.SITE_URL}{reverse('digital_products:download_file', kwargs={'purchase_id': purchase.id, 'file_id': file.id})}"
                link_data['file_size'] = file.file_size

            # Add URL access link if it's a URL
            if file.is_url:
                link_data['content_url'] = f"{settings.SITE_URL}{reverse('digital_products:access_url', kwargs={'purchase_id': purchase.id, 'file_id': file.id})}"
                link_data['is_video'] = file.is_video_url

            download_links.append(link_data)

        products_data.append({
            'product': product,
            'purchase': purchase,
            'download_links': download_links
        })

    context = {
        'student': student,
        'products_data': products_data,
        'total_products': len(purchases),
        'site_name': getattr(settings, 'SITE_NAME', 'RecorderEd'),
        'site_url': settings.SITE_URL,
        'my_purchases_url': f"{settings.SITE_URL}{reverse('digital_products:my_purchases')}"
    }

    # Render email
    subject = f"Download Your {len(purchases)} Purchase(s)"
    html_message = render_to_string('digital_products/emails/cart_purchase_confirmation.html', context)
    plain_message = render_to_string('digital_products/emails/cart_purchase_confirmation.txt', context)

    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[student.email],
        html_message=html_message,
        fail_silently=False,
    )


def send_review_notification(review):
    """
    Notify teacher when a student leaves a review.

    Args:
        review: ProductReview instance
    """
    product = review.product
    teacher = product.teacher

    context = {
        'teacher': teacher,
        'student': review.student,
        'product': product,
        'review': review,
        'site_name': getattr(settings, 'SITE_NAME', 'RecorderEd'),
        'product_url': f"{settings.SITE_URL}{product.get_absolute_url()}"
    }

    subject = f"New {review.rating}-Star Review: {product.title}"
    html_message = render_to_string('digital_products/emails/review_notification.html', context)
    plain_message = render_to_string('digital_products/emails/review_notification.txt', context)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[teacher.email],
        html_message=html_message,
        fail_silently=False,
    )
