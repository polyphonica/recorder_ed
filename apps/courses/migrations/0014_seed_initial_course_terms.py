# Generated manually on 2025-11-21

from django.db import migrations
from django.utils import timezone


INITIAL_TERMS_CONTENT = """# Course Terms and Conditions

**Last Updated: 21 November 2025**
**Version: 1.0**

## 1. Acceptance of Terms

By enrolling in any course on Recorder-ed, you agree to be bound by these Terms and Conditions. Please read them carefully before completing your enrollment.

## 2. Course Enrollment and Payment

2.1. Enrollment in a course is only confirmed upon receipt of full payment.

2.2. All prices are displayed in British Pounds (£) and include any applicable taxes.

2.3. Payment is processed securely through our payment provider, Stripe.

2.4. Once enrolled, you will have unlimited access to the course content for the duration specified (typically lifetime access unless otherwise stated).

## 3. Cancellation and Refund Policy

3.1. **7-Day Trial Period:**
   - You may cancel your course enrollment within **7 days of purchase** for a **full refund**, no questions asked.
   - This trial period allows you to explore the course content and decide if it's right for you.

3.2. **After Trial Period:**
   - After the 7-day trial period has expired, **no refunds** will be provided.
   - Course access will continue for the full access period.

3.3. **Refund Processing:**
   - All eligible refunds will be processed to the original payment method within 5-10 business days.
   - Refund requests must be submitted through your account dashboard.

3.4. **Cancellations by Recorder-ed:**
   - If we discontinue a course you've enrolled in, you will receive a full refund.

## 4. Course Content and Quality

4.1. **No Guarantee of Content:** Course content, teaching methods, and difficulty levels are determined by individual instructors. Recorder-ed does not guarantee the suitability, quality, or appropriateness of course content for any particular learner.

4.2. **Content Review During Trial:** We strongly encourage you to thoroughly review course content during the 7-day trial period. Refunds will not be provided after this period if you find the content unsatisfactory.

4.3. **Skill Level:** It is your responsibility to ensure that you or your child meets any stated prerequisites and that the course difficulty level is appropriate for your needs.

4.4. **Teaching Style:** Each instructor has their own teaching methodology. Differences in teaching style do not constitute grounds for a refund after the trial period.

4.5. **Content Updates:** Instructors may update course content over time to improve quality or relevance. Such updates do not affect your enrollment or access rights.

## 5. Course Access and Technical Requirements

5.1. **Internet Connection:** You are responsible for ensuring you have the necessary equipment and internet connection to access course materials. Technical difficulties on your end do not extend the trial period or constitute grounds for a refund after the trial period.

5.2. **Browser Requirements:** Course content is optimized for modern web browsers. Ensure your browser is up to date for the best experience.

5.3. **Account Security:** You are responsible for maintaining the confidentiality of your account credentials. Do not share your login information with others.

5.4. **Materials:** Unless explicitly stated in the course description, students are responsible for providing their own instruments, materials, and equipment mentioned in the course.

## 6. Student Conduct

6.1. All students are expected to behave respectfully in course messaging and community features.

6.2. Recorder-ed and course instructors reserve the right to revoke access for any student who behaves disruptively or inappropriately. No refund will be provided in such cases.

6.3. For children's courses, parents/guardians are responsible for supervising their child's participation.

## 7. Progress and Completion

7.1. **Self-Paced Learning:** Most courses are self-paced. You may progress through content at your own speed during your access period.

7.2. **Certificates:** Certificates of completion, if offered, are issued upon successful completion of all course requirements including lessons and quizzes.

7.3. **No Guarantee of Results:** While we strive to provide quality education, we cannot guarantee specific learning outcomes or skill attainment.

## 8. Liability and Disclaimers

8.1. **Limitation of Liability:** Recorder-ed acts as a platform connecting students with independent course instructors. We are not responsible for the acts, omissions, or conduct of instructors.

8.2. **No Warranties:** Courses are provided "as is" without any warranties, express or implied, including but not limited to warranties of educational quality, fitness for a particular purpose, or achievement of learning outcomes.

8.3. **Maximum Liability:** In no event shall Recorder-ed's total liability exceed the amount you paid for the course enrollment.

## 9. Data Protection and Privacy

9.1. We collect and process personal data in accordance with UK GDPR and our Privacy Policy.

9.2. By enrolling in a course, you consent to us sharing your contact information with the course instructor for educational purposes.

9.3. Instructors may not use your personal data for any purpose other than delivering the course without your explicit consent.

9.4. **Children's Data:** For participants under 18, we collect data only with parental/guardian consent and in accordance with applicable child protection laws.

## 10. Intellectual Property

10.1. Course materials, videos, handouts, quizzes, and other content provided by instructors are for your personal, non-commercial use only and may not be shared, reproduced, distributed, or resold without permission.

10.2. Instructors retain all intellectual property rights to their course content.

10.3. Violation of intellectual property rights may result in immediate termination of access without refund and potential legal action.

## 11. Recording and Screenshots

11.1. You may not record, screenshot, or otherwise capture course videos or materials for redistribution.

11.2. You may take notes and screenshots for your own personal learning purposes only.

## 12. Age Requirements

12.1. For adult courses, students must be 18 years or older unless otherwise stated.

12.2. For children's courses, enrollments must be made by a parent or legal guardian.

12.3. Age restrictions stated in course descriptions must be adhered to.

## 13. Course Changes and Discontinuation

13.1. Instructors reserve the right to make updates and improvements to course content.

13.2. If a course is discontinued, enrolled students will typically retain access through their access period or receive a pro-rated refund at our discretion.

## 14. Platform Changes

14.1. Recorder-ed reserves the right to modify these Terms and Conditions at any time.

14.2. Changes will be effective immediately upon posting to the website.

14.3. Your continued use of the platform after changes constitutes acceptance of the modified terms.

14.4. For existing enrollments, the terms in effect at the time of your enrollment will apply.

## 15. Dispute Resolution

15.1. We encourage you to contact us directly to resolve any disputes or concerns.

15.2. These terms are governed by the laws of England and Wales.

15.3. Any disputes shall be subject to the exclusive jurisdiction of the courts of England and Wales.

## 16. Contact Information

If you have any questions about these Terms and Conditions, please contact us at:
- Email: support@recorder-ed.com
- Website: www.recorder-ed.com

## 17. Severability

If any provision of these Terms and Conditions is found to be unenforceable or invalid, that provision shall be limited or eliminated to the minimum extent necessary, and the remaining provisions shall remain in full force and effect.

---

**By checking the acceptance box and proceeding with payment, you acknowledge that you have read, understood, and agree to be bound by these Terms and Conditions.**
"""


def seed_initial_terms(apps, schema_editor):
    """Create initial version of Course Terms and Conditions"""
    CourseTermsAndConditions = apps.get_model('courses', 'CourseTermsAndConditions')

    # Create initial terms
    CourseTermsAndConditions.objects.create(
        version=1,
        content=INITIAL_TERMS_CONTENT,
        effective_date=timezone.now(),
        is_current=True,
    )


def reverse_seed(apps, schema_editor):
    """Remove seeded terms if migration is reversed"""
    CourseTermsAndConditions = apps.get_model('courses', 'CourseTermsAndConditions')
    CourseTermsAndConditions.objects.filter(version=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0013_coursetermsandconditions_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_initial_terms, reverse_seed),
    ]
