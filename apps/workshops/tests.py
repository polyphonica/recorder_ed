from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import ChildProfile
from .models import (
    Workshop, WorkshopSession, WorkshopRegistration, WorkshopCompetition,
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
