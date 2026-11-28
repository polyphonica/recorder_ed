import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.audioplayer.models import Piece, PieceCollection

from .models import Task
from .views import make_link_token


def _user(username, teacher=True):
    user = get_user_model().objects.create_user(username, email=f'{username}@example.com', password='x')
    user.profile.is_teacher = teacher
    user.profile.profile_completed = True
    user.profile.email_verified = True
    user.profile.save()
    return user


@override_settings(ALLOWED_HOSTS=['testserver'])
class TaskTests(TestCase):
    def setUp(self):
        self.teacher = _user('t1')
        self.client.force_login(self.teacher)
        self.today = timezone.localdate()

    def add(self, **data):
        data.setdefault('area', 'general')
        return self.client.post(reverse('teacher_tasks:create'), data)

    def test_add_and_list_in_groups(self):
        self.add(title='Overdue', due_date=self.today - datetime.timedelta(days=1))
        self.add(title='Today', due_date=self.today)
        self.add(title='Soon', due_date=self.today + datetime.timedelta(days=3))
        self.add(title='Someday')
        response = self.client.get(reverse('teacher_tasks:list'))
        groups = {key: [t.title for t in tasks] for key, label, tasks in response.context['groups']}
        self.assertEqual(groups, {'overdue': ['Overdue'], 'today': ['Today'], 'week': ['Soon'], 'later': ['Someday']})

    def test_toggle_edit_delete(self):
        self.add(title='Draft')
        task = Task.objects.get()
        self.client.post(reverse('teacher_tasks:toggle', kwargs={'pk': task.pk}))
        task.refresh_from_db()
        self.assertTrue(task.is_done)
        self.client.post(reverse('teacher_tasks:toggle', kwargs={'pk': task.pk}))
        task.refresh_from_db()
        self.assertFalse(task.is_done)
        self.client.post(reverse('teacher_tasks:update', kwargs={'pk': task.pk}),
                         {'title': 'Final', 'notes': 'n', 'area': 'courses', 'due_date': ''})
        task.refresh_from_db()
        self.assertEqual((task.title, task.area), ('Final', 'courses'))
        self.client.post(reverse('teacher_tasks:delete', kwargs={'pk': task.pk}))
        self.assertFalse(Task.objects.exists())

    def test_other_teachers_tasks_are_private(self):
        other = _user('t2')
        task = Task.objects.create(owner=other, title='Theirs')
        self.assertEqual(self.client.post(reverse('teacher_tasks:toggle', kwargs={'pk': task.pk})).status_code, 404)
        self.assertNotContains(self.client.get(reverse('teacher_tasks:list')), 'Theirs')

    def test_students_cannot_use_tasks(self):
        self.client.force_login(_user('s1', teacher=False))
        self.assertEqual(self.client.get(reverse('teacher_tasks:list')).status_code, 302)

    def test_area_filter(self):
        self.add(title='Course job', area='courses')
        self.add(title='General job')
        response = self.client.get(reverse('teacher_tasks:list'), {'area': 'courses'})
        titles = [t.title for _, _, tasks in response.context['groups'] for t in tasks]
        self.assertEqual(titles, ['Course job'])

    def test_link_to_own_piece_sets_area_and_shows_on_its_page(self):
        piece = Piece.objects.create(title='Sonata', created_by=self.teacher)
        self.add(title='Add a PDF', link=make_link_token(piece))
        task = Task.objects.get()
        self.assertEqual(task.area, 'playalongs')
        self.assertEqual(task.link['url'], reverse('audioplayer:piece_edit', kwargs={'pk': piece.pk}))
        html = self.client.get(reverse('audioplayer:piece_edit', kwargs={'pk': piece.pk})).content.decode()
        self.assertIn('Tasks for Sonata', html)
        self.assertIn('Add a PDF', html)

    def test_cannot_link_to_someone_elses_item(self):
        other = _user('t3')
        piece = Piece.objects.create(title='Theirs', created_by=other)
        response = self.add(title='Sneaky', link=make_link_token(piece))
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Task.objects.exists())

    def test_tampered_link_is_rejected(self):
        self.assertEqual(self.add(title='x', link='not-a-token').status_code, 404)

    def test_deleting_linked_item_keeps_task_without_link(self):
        col = PieceCollection.objects.create(title='Duets', created_by=self.teacher)
        self.add(title='Check duets', link=make_link_token(col))
        col.delete()
        task = Task.objects.get()
        self.assertIsNone(task.link)
        self.assertEqual(task.content_type, None)

    def test_menu_badge_and_home_card(self):
        self.add(title='Due now', due_date=self.today)
        self.add(title='Later')
        response = self.client.get('/')
        self.assertEqual(response.context['teacher_tasks_due'], 1)
        self.assertEqual([t.title for t in response.context['tasks_today']], ['Due now'])
        self.assertEqual([t.title for t in response.context['tasks_next']], ['Later'])
        self.assertContains(response, reverse('teacher_tasks:list'))


@override_settings(ALLOWED_HOSTS=['testserver'])
class TeacherDashboardLinkTests(TestCase):
    def test_teachers_have_a_dashboard_link_everywhere(self):
        self.client.force_login(_user('dash_teacher'))
        html = self.client.get(reverse('teacher_tasks:list')).content.decode()
        self.assertIn('<i class="fas fa-home mr-1"></i>Dashboard', html)
        self.assertIn('My Dashboard', html)
        self.assertIn('title="Your dashboard"', html)
        # Highlighted on the dashboard itself
        home = self.client.get('/').content.decode()
        self.assertIn('font-bold bg-primary text-primary-content"><i class="fas fa-home mr-1"></i>Dashboard', home)

    def test_students_menus_unchanged(self):
        self.client.force_login(_user('dash_student', teacher=False))
        html = self.client.get('/').content.decode()
        self.assertNotIn('My Dashboard', html)
        self.assertNotIn('title="Your dashboard"', html)
