from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import ChildProfile
from .forms import WorkshopForm
from .models import (
    Workshop, WorkshopCategory, WorkshopSession, WorkshopRegistration, WorkshopCompetition,
    WorkshopCompetitionAnswer, WorkshopCompetitionEntry,
)
from .notifications import WorkshopCompetitionNotificationService


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class CompetitionEmailTests(TestCase):
    """Emails sent when a competition is created and when its winner is drawn."""

    def setUp(self):
        self.instructor = User.objects.create_user(
            'teacher', 'teacher@example.com', 'pw', first_name='Tina', last_name='Teacher'
        )
        self.instructor.profile.is_teacher = True
        self.instructor.profile.profile_completed = True  # else ProfileCompletionMiddleware redirects
        self.instructor.profile.save()

        self.workshop = Workshop.objects.create(
            title='Recorder Ornamentation', slug='recorder-ornamentation',
            description='d', short_description='s', learning_objectives='l',
            instructor=self.instructor,
        )
        start = timezone.now() + timedelta(days=7)
        self.session = WorkshopSession.objects.create(
            workshop=self.workshop, start_datetime=start, end_datetime=start + timedelta(hours=1),
        )

    def _student(self, username, **kwargs):
        return User.objects.create_user(
            username, f'{username}@example.com', 'pw', first_name=username.title(), **kwargs
        )

    def _register(self, student, status='registered', **kwargs):
        return WorkshopRegistration.objects.create(
            session=self.session, student=student, status=status,
            email=kwargs.pop('email', student.email), **kwargs
        )

    def _competition(self, **kwargs):
        competition = WorkshopCompetition.objects.create(
            session=self.session, question='Which finger covers the thumb hole?', **kwargs
        )
        self.correct = WorkshopCompetitionAnswer.objects.create(
            competition=competition, text='Left thumb', is_correct=True, order=0
        )
        self.wrong = WorkshopCompetitionAnswer.objects.create(
            competition=competition, text='Right pinky', is_correct=False, order=1
        )
        return competition

    def _post_data(self, **overrides):
        data = {
            'question': 'Which finger covers the thumb hole?',
            'draw_datetime': '',
            'answers-TOTAL_FORMS': '2',
            'answers-INITIAL_FORMS': '0',
            'answers-MIN_NUM_FORMS': '2',
            'answers-MAX_NUM_FORMS': '1000',
            'answers-0-text': 'Left thumb',
            'answers-0-is_correct': 'on',
            'answers-0-order': '0',
            'answers-1-text': 'Right pinky',
            'answers-1-order': '1',
        }
        data.update(overrides)
        return data

    # --- announcement ---------------------------------------------------

    def test_announcement_sent_only_to_eligible_registrations(self):
        registered = self._student('reg')
        promoted = self._student('promo')
        attended = self._student('att')
        waitlisted = self._student('wait')
        cancelled = self._student('cancel')
        self._register(registered)
        self._register(promoted, status='promoted')
        self._register(attended, status='attended')
        self._register(waitlisted, status='waitlisted')
        self._register(cancelled, status='cancelled')
        competition = self._competition()

        sent = WorkshopCompetitionNotificationService.send_competition_announcement(competition)

        self.assertEqual(sent, 3)
        recipients = sorted(m.to[0] for m in mail.outbox)
        self.assertEqual(recipients, ['att@example.com', 'promo@example.com', 'reg@example.com'])

    def test_announcement_contains_question_and_entry_instructions(self):
        self._register(self._student('reg'))
        competition = self._competition()

        WorkshopCompetitionNotificationService.send_competition_announcement(competition)

        message = mail.outbox[0]
        enter_path = reverse('workshops:enter_competition', kwargs={'competition_id': competition.id})
        self.assertIn('Recorder Ornamentation', message.subject)
        self.assertIn('Which finger covers the thumb hole?', message.body)
        self.assertIn('HOW TO ENTER', message.body)
        self.assertIn(enter_path, message.body)
        html = message.alternatives[0][0]
        self.assertIn(enter_path, html)
        self.assertIn('Which finger covers the thumb hole?', html)
        self.assertIn('Tina Teacher', message.body)

    def test_announcement_mentions_draw_time_only_when_set(self):
        self._register(self._student('reg'))
        competition = self._competition()
        WorkshopCompetitionNotificationService.send_competition_announcement(competition)
        self.assertNotIn('will be drawn after', mail.outbox[0].body)

        mail.outbox.clear()
        competition.draw_datetime = timezone.now() + timedelta(days=8)
        competition.save()
        WorkshopCompetitionNotificationService.send_competition_announcement(competition)
        self.assertIn('will be drawn after', mail.outbox[0].body)

    def test_guardian_with_two_children_gets_one_email_at_guardian_address(self):
        guardian = self._student('guardian')
        for name in ('Amy', 'Ben'):
            child = ChildProfile.objects.create(
                guardian=guardian, first_name=name, last_name='Kid', date_of_birth=date(2015, 1, 1)
            )
            self._register(guardian, child_profile=child, email='parent@example.org')
        competition = self._competition()

        sent = WorkshopCompetitionNotificationService.send_competition_announcement(competition)

        self.assertEqual(sent, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['parent@example.org'])

    def test_opted_out_student_is_skipped(self):
        opted_out = self._student('quiet')
        opted_out.profile.workshop_email_notifications = False
        opted_out.profile.save()
        self._register(opted_out)
        self._register(self._student('reg'))
        competition = self._competition()

        sent = WorkshopCompetitionNotificationService.send_competition_announcement(competition)

        self.assertEqual(sent, 1)
        self.assertEqual(mail.outbox[0].to, ['reg@example.com'])

    def test_registrations_for_other_sessions_are_not_emailed(self):
        other_session = WorkshopSession.objects.create(
            workshop=self.workshop,
            start_datetime=self.session.start_datetime + timedelta(days=1),
            end_datetime=self.session.end_datetime + timedelta(days=1),
        )
        other_student = self._student('other')
        WorkshopRegistration.objects.create(
            session=other_session, student=other_student, email=other_student.email
        )
        competition = self._competition()

        sent = WorkshopCompetitionNotificationService.send_competition_announcement(competition)

        self.assertEqual(sent, 0)
        self.assertEqual(len(mail.outbox), 0)

    # --- winner ---------------------------------------------------------

    def test_winner_notification_goes_to_winner_only(self):
        winner = self._student('champ')
        loser = self._student('loser')
        competition = self._competition()
        winning_entry = WorkshopCompetitionEntry.objects.create(
            competition=competition, participant=winner, selected_answer=self.correct
        )
        WorkshopCompetitionEntry.objects.create(
            competition=competition, participant=loser, selected_answer=self.correct
        )
        competition.winner = winning_entry
        competition.save()

        result = WorkshopCompetitionNotificationService.send_winner_notification(competition)

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['champ@example.com'])
        self.assertIn('You won', mail.outbox[0].subject)
        self.assertIn('Recorder Ornamentation', mail.outbox[0].body)
        self.assertIn('Tina Teacher', mail.outbox[0].body)

    def test_winner_notification_names_child_when_child_won(self):
        guardian = self._student('guardian')
        child = ChildProfile.objects.create(
            guardian=guardian, first_name='Amy', last_name='Kid', date_of_birth=date(2015, 1, 1)
        )
        competition = self._competition()
        entry = WorkshopCompetitionEntry.objects.create(
            competition=competition, participant=guardian,
            child_profile=child, selected_answer=self.correct,
        )
        competition.winner = entry
        competition.save()

        WorkshopCompetitionNotificationService.send_winner_notification(competition)

        self.assertIn('Amy Kid has', mail.outbox[0].body)

    def test_winner_notification_sent_even_if_workshop_emails_opted_out(self):
        winner = self._student('champ')
        winner.profile.workshop_email_notifications = False
        winner.profile.save()
        competition = self._competition()
        competition.winner = WorkshopCompetitionEntry.objects.create(
            competition=competition, participant=winner, selected_answer=self.correct
        )
        competition.save()

        self.assertTrue(WorkshopCompetitionNotificationService.send_winner_notification(competition))
        self.assertEqual(len(mail.outbox), 1)

    def test_winner_notification_without_winner_sends_nothing(self):
        competition = self._competition()
        self.assertFalse(WorkshopCompetitionNotificationService.send_winner_notification(competition))
        self.assertEqual(len(mail.outbox), 0)

    # --- view wiring ----------------------------------------------------

    def test_creating_competition_emails_registered_participants(self):
        self._register(self._student('reg'))
        self.client.force_login(self.instructor)

        response = self.client.post(
            reverse('workshops:create_competition', kwargs={'session_id': self.session.id}),
            self._post_data(),
        )

        competition = WorkshopCompetition.objects.get(session=self.session)
        self.assertRedirects(
            response, reverse('workshops:manage_competition', kwargs={'competition_id': competition.id})
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['reg@example.com'])

    def test_email_failure_does_not_block_competition_creation(self):
        self._register(self._student('reg'))
        self.client.force_login(self.instructor)

        with patch.object(
            WorkshopCompetitionNotificationService, 'send_competition_announcement',
            side_effect=RuntimeError('smtp down'),
        ):
            response = self.client.post(
                reverse('workshops:create_competition', kwargs={'session_id': self.session.id}),
                self._post_data(),
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(WorkshopCompetition.objects.filter(session=self.session).exists())

    def test_drawing_winner_emails_the_winner(self):
        winner = self._student('champ')
        competition = self._competition()
        WorkshopCompetitionEntry.objects.create(
            competition=competition, participant=winner, selected_answer=self.correct
        )
        WorkshopCompetitionEntry.objects.create(
            competition=competition, participant=self._student('loser'), selected_answer=self.wrong
        )
        self.client.force_login(self.instructor)

        response = self.client.post(
            reverse('workshops:draw_winner', kwargs={'competition_id': competition.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['champ@example.com'])

    def test_locked_or_empty_draw_sends_no_email(self):
        competition = self._competition(draw_datetime=timezone.now() + timedelta(days=1))
        WorkshopCompetitionEntry.objects.create(
            competition=competition, participant=self._student('champ'), selected_answer=self.correct
        )
        self.client.force_login(self.instructor)
        url = reverse('workshops:draw_winner', kwargs={'competition_id': competition.id})

        self.assertEqual(self.client.post(url).status_code, 403)

        competition.draw_datetime = None
        competition.save()
        competition.entries.all().delete()
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertEqual(len(mail.outbox), 0)


class WorkshopCategoryRequiredTests(TestCase):
    """A workshop can't be saved without a category (choose one, or type a new one)."""

    def setUp(self):
        self.instructor = User.objects.create_user('teacher', 'teacher@example.com', 'pw')
        self.category = WorkshopCategory.objects.create(name='Technique', slug='technique')

    def _form(self, **overrides):
        data = {
            'title': 'Articulation', 'slug': 'articulation',
            'short_description': 's', 'description': 'd', 'learning_objectives': 'l',
            'difficulty_level': 'beginner', 'delivery_method': 'online',
            'duration_value': 60, 'duration_unit': 'minutes',
            'is_free': 'on', 'status': 'draft',
        }
        data.update(overrides)
        return WorkshopForm(data=data)

    def test_form_rejects_missing_category(self):
        form = self._form()
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)

    def test_form_rejects_blank_new_category_name(self):
        form = self._form(new_category_name='   ')
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)

    def test_form_accepts_selected_category(self):
        form = self._form(category=self.category.id)
        self.assertNotIn('category', form.errors)

    def test_form_accepts_new_category_name_and_creates_it_on_save(self):
        form = self._form(new_category_name='Ensemble Playing')
        self.assertNotIn('category', form.errors)
        self.assertTrue(form.is_valid(), form.errors)
        workshop = form.save(commit=False)
        workshop.instructor = self.instructor
        workshop.save()
        self.assertEqual(workshop.category.name, 'Ensemble Playing')

    def test_model_validation_rejects_missing_category(self):
        """Covers the admin, which validates through the model rather than WorkshopForm."""
        workshop = Workshop(
            title='X', slug='x', description='d', short_description='s',
            learning_objectives='l', instructor=self.instructor,
        )
        with self.assertRaises(ValidationError) as ctx:
            workshop.full_clean()
        self.assertIn('category', ctx.exception.message_dict)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class InterestNotificationTests(TestCase):
    """People who registered interest get one email per batch of new dates."""

    def setUp(self):
        from .models import WorkshopInterest
        self.instructor = User.objects.create_user(
            'teacher', 'teacher@example.com', 'pw', first_name='Tina', last_name='Teacher'
        )
        self.workshop = Workshop.objects.create(
            title='Baroque Articulation', slug='baroque-articulation',
            description='d', short_description='s', learning_objectives='l',
            instructor=self.instructor, status=Workshop.Status.PUBLISHED,
        )
        self.member = User.objects.create_user('sam', 'sam@example.com', 'pw', first_name='Sam')
        self.member_interest = WorkshopInterest.objects.create(
            workshop=self.workshop, user=self.member, email='sam@example.com',
        )
        self.guest_interest = WorkshopInterest.objects.create(
            workshop=self.workshop, email='guest@example.com',
        )
        mail.outbox = []

    def _session(self, days):
        start = timezone.now() + timedelta(days=days)
        return WorkshopSession(
            workshop=self.workshop, start_datetime=start, end_datetime=start + timedelta(hours=2),
        )

    def _create_session(self, days):
        with self.captureOnCommitCallbacks(execute=True):
            session = self._session(days)
            session.save()
        return session

    def _bulk_create(self, *days):
        from .signals import queue_interest_notifications
        with self.captureOnCommitCallbacks(execute=True):
            WorkshopSession.objects.bulk_create([self._session(d) for d in days])
            queue_interest_notifications(self.workshop.pk)

    def _emails_to(self, address):
        return [m for m in mail.outbox if address in m.to]

    def test_single_session_emails_each_interested_person_once(self):
        self._create_session(7)
        self.assertEqual(len(mail.outbox), 2)
        member_mail = self._emails_to('sam@example.com')[0]
        self.assertEqual(member_mail.subject, 'New date for Baroque Articulation')
        self.assertIn('Hi Sam', member_mail.body)
        self.assertIn('Hi there', self._emails_to('guest@example.com')[0].body)

    def test_batch_sends_one_email_listing_every_date(self):
        self._bulk_create(7, 14, 21)
        self.assertEqual(len(mail.outbox), 2)
        member_mail = self._emails_to('sam@example.com')[0]
        self.assertEqual(member_mail.subject, '3 new dates for Baroque Articulation')
        self.assertEqual(member_mail.body.count('- Date:'), 3)

    def test_later_sessions_trigger_a_new_email_with_only_the_new_dates(self):
        self._create_session(7)
        mail.outbox = []
        self._bulk_create(30, 37)
        member_mail = self._emails_to('sam@example.com')[0]
        self.assertEqual(member_mail.subject, '2 new dates for Baroque Articulation')
        self.assertEqual(member_mail.body.count('- Date:'), 2)

    def test_draft_workshop_holds_emails_until_published(self):
        self.workshop.status = Workshop.Status.DRAFT
        self.workshop.save()
        self._bulk_create(7, 14)
        self.assertEqual(mail.outbox, [])

        with self.captureOnCommitCallbacks(execute=True):
            self.workshop.status = Workshop.Status.PUBLISHED
            self.workshop.save(update_fields=['status'])
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(self._emails_to('sam@example.com')[0].subject,
                         '2 new dates for Baroque Articulation')

    def test_resaving_published_workshop_does_not_resend(self):
        self._create_session(7)
        mail.outbox = []
        with self.captureOnCommitCallbacks(execute=True):
            self.workshop.save()
        self.assertEqual(mail.outbox, [])

    def test_past_cancelled_and_opted_out_are_skipped(self):
        self.guest_interest.notify_immediately = False
        self.guest_interest.save()
        cancelled = self._session(7)
        cancelled.is_cancelled = True
        with self.captureOnCommitCallbacks(execute=True):
            cancelled.save()
            past = self._session(-3)
            past.save()
        self.assertEqual(mail.outbox, [])

    def test_html_version_lists_each_date(self):
        self._bulk_create(7, 14)
        html = self._emails_to('guest@example.com')[0].alternatives[0][0]
        self.assertIn('Hi there', html)
        self.assertEqual(html.count('Register for this date'), 2)


class DuplicateWorkshopTests(TestCase):
    """Duplicating a workshop: details, image, sessions on new dates, materials."""

    def setUp(self):
        import shutil, tempfile
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import WorkshopMaterial

        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        media_override = override_settings(MEDIA_ROOT=self.media)
        media_override.enable()
        self.addCleanup(media_override.disable)

        self.instructor = User.objects.create_user('teacher', 'teacher@example.com', 'pw')
        self.instructor.profile.is_teacher = True
        self.instructor.profile.profile_completed = True
        self.instructor.profile.save()
        self.client.force_login(self.instructor)

        self.category = WorkshopCategory.objects.create(name='Technique', slug='technique')
        self.original = Workshop.objects.create(
            title='Baroque Articulation', slug='baroque-articulation',
            description='d', short_description='s', learning_objectives='l',
            instructor=self.instructor, category=self.category,
            status=Workshop.Status.PUBLISHED, is_featured=True,
            is_free=False, price=25, venue_name="St John's Hall",
            featured_image=SimpleUploadedFile('cover_optimized.jpg', b'fake-jpeg', content_type='image/jpeg'),
        )
        from zoneinfo import ZoneInfo
        london = ZoneInfo('Europe/London')
        from datetime import datetime
        # Two sessions a week apart in October (BST), 10:00 London time
        self.s1 = WorkshopSession.objects.create(
            workshop=self.original, timezone_name='Europe/London',
            start_datetime=datetime(2026, 10, 3, 10, 0, tzinfo=london),
            end_datetime=datetime(2026, 10, 3, 12, 0, tzinfo=london),
            session_title='Part 1', meeting_url='https://zoom.example/old', max_participants=12,
        )
        self.s2 = WorkshopSession.objects.create(
            workshop=self.original, timezone_name='Europe/London',
            start_datetime=datetime(2026, 10, 10, 10, 0, tzinfo=london),
            end_datetime=datetime(2026, 10, 10, 12, 0, tzinfo=london),
            session_title='Part 2',
        )
        WorkshopSession.objects.create(
            workshop=self.original, is_cancelled=True,
            start_datetime=datetime(2026, 10, 17, 10, 0, tzinfo=london),
            end_datetime=datetime(2026, 10, 17, 12, 0, tzinfo=london),
        )
        WorkshopMaterial.objects.create(
            workshop=self.original, title='Reading list', material_type='link',
            external_url='https://example.com/list',
        )
        WorkshopMaterial.objects.create(
            workshop=self.original, session=self.s2, title='Part 2 handout', material_type='document',
            file=SimpleUploadedFile('handout.pdf', b'%PDF-fake', content_type='application/pdf'),
        )

    def _duplicate(self, **data):
        data.setdefault('title', 'Baroque Articulation')
        return self.client.post(
            reverse('workshops:duplicate_workshop', args=[self.original.slug]), data
        )

    def _copy(self):
        return Workshop.objects.exclude(pk=self.original.pk).get()

    def test_copies_details_as_unfeatured_draft_with_own_image_file(self):
        response = self._duplicate()
        copy = self._copy()
        self.assertRedirects(response, reverse('workshops:edit_workshop', args=[copy.slug]),
                             fetch_redirect_response=False)
        self.assertEqual(copy.slug, 'baroque-articulation-2')
        self.assertEqual(copy.status, Workshop.Status.DRAFT)
        self.assertFalse(copy.is_featured)
        self.assertEqual((copy.price, copy.venue_name, copy.category), (25, "St John's Hall", self.category))
        self.assertTrue(copy.featured_image)
        self.assertNotEqual(copy.featured_image.name, self.original.featured_image.name)
        self.assertEqual(copy.sessions.count(), 0)
        self.assertEqual(copy.materials.count(), 0)

    def test_sessions_shift_keeping_spacing_and_local_time_across_clock_change(self):
        from datetime import date
        from zoneinfo import ZoneInfo
        response = self._duplicate(copy_sessions='on', first_session_date='2027-01-09')
        copy = self._copy()
        self.assertRedirects(response, reverse('workshops:manage_sessions', args=[copy.slug]),
                             fetch_redirect_response=False)
        sessions = list(copy.sessions.order_by('start_datetime'))
        self.assertEqual(len(sessions), 2)  # cancelled session not copied
        london = ZoneInfo('Europe/London')
        starts = [s.start_datetime.astimezone(london) for s in sessions]
        self.assertEqual([d.date() for d in starts], [date(2027, 1, 9), date(2027, 1, 16)])
        self.assertTrue(all((d.hour, d.minute) == (10, 0) for d in starts))  # still 10:00 in GMT
        self.assertEqual([s.session_title for s in sessions], ['Part 1', 'Part 2'])
        self.assertEqual(sessions[0].max_participants, 12)
        self.assertEqual(sessions[0].meeting_url, '')
        self.assertEqual(sessions[0].current_registrations, 0)
        copy.refresh_from_db()
        self.assertEqual(copy.total_sessions, 2)

    def test_materials_follow_their_sessions(self):
        self._duplicate(copy_sessions='on', first_session_date='2027-01-09', copy_materials='on')
        copy = self._copy()
        handout = copy.materials.get(title='Part 2 handout')
        self.assertEqual(handout.session.session_title, 'Part 2')
        self.assertNotEqual(handout.file.name, 'workshops/materials/handout.pdf')
        self.assertTrue(copy.materials.filter(title='Reading list', session=None).exists())

    def test_materials_without_sessions_copies_workshop_wide_only(self):
        self._duplicate(copy_materials='on')
        self.assertEqual(list(self._copy().materials.values_list('title', flat=True)), ['Reading list'])

    def test_copy_sessions_requires_a_future_date(self):
        self._duplicate(copy_sessions='on')
        self._duplicate(copy_sessions='on', first_session_date='2020-01-01')
        self.assertEqual(Workshop.objects.count(), 1)

    def test_cannot_duplicate_another_instructors_workshop(self):
        other = User.objects.create_user('other', 'other@example.com', 'pw')
        other.profile.profile_completed = True
        other.profile.save()
        self.client.force_login(other)
        self.assertEqual(self._duplicate().status_code, 404)

    def test_workshop_list_renders_duplicate_dialog(self):
        response = self.client.get(reverse('workshops:instructor_workshops'))
        self.assertContains(response, f'id="duplicate-{self.original.pk}"')
        self.assertContains(response, 'name="first_session_date"')


class VenueTests(TestCase):
    """Saved venues: saving from the workshop wizard, filling it, and My Venues."""

    def setUp(self):
        from .models import Venue
        self.Venue = Venue
        self.instructor = User.objects.create_user('teacher', 'teacher@example.com', 'pw')
        self.instructor.profile.is_teacher = True
        self.instructor.profile.profile_completed = True
        self.instructor.profile.save()
        self.client.force_login(self.instructor)
        self.category = WorkshopCategory.objects.create(name='Technique', slug='technique')

    def _workshop_data(self, **overrides):
        data = {
            'title': 'Articulation', 'slug': 'articulation', 'category': self.category.id,
            'short_description': 's', 'description': 'd', 'learning_objectives': 'l',
            'difficulty_level': 'beginner', 'delivery_method': 'in_person',
            'duration_value': 60, 'duration_unit': 'minutes',
            'is_free': 'on', 'status': 'draft',
            'venue_name': "St John's Hall", 'venue_address': '1 Church Lane',
            'venue_city': 'Bristol', 'venue_postcode': 'BS1 1AA',
            'venue_notes': 'Side door', 'max_venue_capacity': 30,
        }
        data.update(overrides)
        return data

    def test_ticking_save_venue_creates_a_saved_venue(self):
        self.client.post(reverse('workshops:create_workshop'), self._workshop_data(save_venue='on'))
        self.assertTrue(Workshop.objects.filter(slug='articulation').exists())
        venue = self.Venue.objects.get(instructor=self.instructor)
        self.assertEqual((venue.name, venue.city, venue.max_capacity, venue.notes),
                         ("St John's Hall", 'Bristol', 30, 'Side door'))

    def test_saving_again_updates_venue_with_same_name(self):
        self.Venue.objects.create(instructor=self.instructor, name="st john's hall", city='Old')
        self.client.post(reverse('workshops:create_workshop'), self._workshop_data(save_venue='on'))
        self.assertEqual(self.Venue.objects.count(), 1)
        self.assertEqual(self.Venue.objects.get().city, 'Bristol')

    def test_not_ticked_or_online_does_not_save(self):
        self.client.post(reverse('workshops:create_workshop'), self._workshop_data())
        self.client.post(reverse('workshops:create_workshop'),
                         self._workshop_data(slug='online-one', delivery_method='online', save_venue='on'))
        self.assertEqual(Workshop.objects.count(), 2)
        self.assertEqual(self.Venue.objects.count(), 0)

    def test_wizard_offers_only_own_saved_venues(self):
        self.Venue.objects.create(instructor=self.instructor, name='Quaker Meeting House', city='Bath')
        other = User.objects.create_user('other', 'o@example.com', 'pw')
        self.Venue.objects.create(instructor=other, name='Secret Studio')
        response = self.client.get(reverse('workshops:create_workshop'))
        self.assertContains(response, 'Quaker Meeting House, Bath')
        self.assertContains(response, 'id="saved-venues-data"')
        self.assertNotContains(response, 'Secret Studio')

    def test_my_venues_add_edit_remove(self):
        self.client.post(reverse('workshops:venue_create'), {'name': 'Hall A', 'city': 'Leeds'})
        venue = self.Venue.objects.get()
        self.assertContains(self.client.get(reverse('workshops:venue_list')), 'Hall A')
        self.client.post(reverse('workshops:venue_edit', args=[venue.pk]), {'name': 'Hall B', 'city': 'York'})
        venue.refresh_from_db()
        self.assertEqual((venue.name, venue.city), ('Hall B', 'York'))
        self.client.post(reverse('workshops:venue_delete', args=[venue.pk]))
        self.assertFalse(self.Venue.objects.exists())

    def test_duplicate_venue_name_rejected(self):
        self.Venue.objects.create(instructor=self.instructor, name='Hall A')
        response = self.client.post(reverse('workshops:venue_create'), {'name': 'hall a'})
        self.assertContains(response, 'already have a saved venue')
        self.assertEqual(self.Venue.objects.count(), 1)

    def test_cannot_touch_another_instructors_venue(self):
        other = User.objects.create_user('other', 'o@example.com', 'pw')
        venue = self.Venue.objects.create(instructor=other, name='Theirs')
        self.assertEqual(self.client.get(reverse('workshops:venue_edit', args=[venue.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('workshops:venue_delete', args=[venue.pk])).status_code, 404)
        self.assertTrue(self.Venue.objects.filter(pk=venue.pk).exists())

    def test_my_venues_requires_instructor(self):
        student = User.objects.create_user('student', 's@example.com', 'pw')
        student.profile.profile_completed = True
        student.profile.save()
        self.client.force_login(student)
        self.assertEqual(self.client.get(reverse('workshops:venue_list')).status_code, 403)
