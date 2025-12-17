from django.test import TestCase
from django.contrib.auth.models import User
from apps.core.notifications import BaseNotificationService
from apps.accounts.models import UserProfile
from unittest.mock import Mock, patch
import logging


class BaseNotificationServiceUtilitiesTestCase(TestCase):
    """Tests for BaseNotificationService utility methods"""

    def setUp(self):
        """Set up test data"""
        # Create test user with email
        self.user_with_email = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        # Profile is auto-created by signal, just retrieve and update it
        self.profile_with_email = self.user_with_email.profile
        self.profile_with_email.workshop_email_notifications = True
        self.profile_with_email.save()

        # Create user without email
        self.user_without_email = User.objects.create_user(
            username='noemail',
            first_name='No',
            last_name='Email'
        )
        self.user_without_email.email = ''
        self.user_without_email.save()

        # Create user with only username
        self.user_username_only = User.objects.create_user(
            username='usernameonly',
            email='username@example.com'
        )

    # ===== validate_email tests =====

    def test_validate_email_success(self):
        """Test validate_email with valid user and email"""
        is_valid, email = BaseNotificationService.validate_email(self.user_with_email)
        self.assertTrue(is_valid)
        self.assertEqual(email, 'test@example.com')

    def test_validate_email_none_user(self):
        """Test validate_email with None user"""
        is_valid, email = BaseNotificationService.validate_email(None)
        self.assertFalse(is_valid)
        self.assertIsNone(email)

    def test_validate_email_no_email(self):
        """Test validate_email with user that has no email"""
        is_valid, email = BaseNotificationService.validate_email(self.user_without_email)
        self.assertFalse(is_valid)
        self.assertIsNone(email)

    def test_validate_email_with_log_prefix(self):
        """Test validate_email with custom log prefix"""
        with self.assertLogs('apps.core.notifications', level='WARNING') as logs:
            is_valid, email = BaseNotificationService.validate_email(
                self.user_without_email,
                'Student'
            )
            self.assertFalse(is_valid)
            self.assertTrue(any('Student' in log for log in logs.output))

    # ===== check_opt_out tests =====

    def test_check_opt_out_no_profile(self):
        """Test check_opt_out when user has no profile"""
        # Delete the auto-created profile to test the no-profile case
        self.user_without_email.profile.delete()
        # user_without_email now has no profile - should default to True (send email)
        result = BaseNotificationService.check_opt_out(self.user_without_email)
        self.assertTrue(result)

    def test_check_opt_out_opted_in(self):
        """Test check_opt_out when user has opted in (field = True)"""
        # User already has profile with workshop_email_notifications = True from setUp
        result = BaseNotificationService.check_opt_out(
            self.user_with_email,
            'workshop_email_notifications'
        )
        self.assertTrue(result)  # Should send email

    def test_check_opt_out_opted_out(self):
        """Test check_opt_out when user has opted out (field = False)"""
        # Update profile to opt out
        self.profile_with_email.workshop_email_notifications = False
        self.profile_with_email.save()

        result = BaseNotificationService.check_opt_out(
            self.user_with_email,
            'workshop_email_notifications'
        )
        self.assertFalse(result)  # Should NOT send email

    def test_check_opt_out_none_user(self):
        """Test check_opt_out with None user"""
        result = BaseNotificationService.check_opt_out(None)
        self.assertTrue(result)  # Default to sending

    def test_check_opt_out_custom_field(self):
        """Test check_opt_out with custom field name"""
        # Set email_on_new_message to True
        self.profile_with_email.email_on_new_message = True
        self.profile_with_email.save()

        result = BaseNotificationService.check_opt_out(
            self.user_with_email,
            'email_on_new_message'
        )
        self.assertTrue(result)

    def test_check_opt_out_missing_field(self):
        """Test check_opt_out when field doesn't exist on profile"""
        # Field 'nonexistent_field' doesn't exist on UserProfile
        result = BaseNotificationService.check_opt_out(
            self.user_with_email,
            'nonexistent_field'
        )
        self.assertTrue(result)  # Default to sending when field missing

    # ===== get_display_name tests =====

    def test_get_display_name_full_name(self):
        """Test get_display_name returns full name when available"""
        name = BaseNotificationService.get_display_name(self.user_with_email)
        self.assertEqual(name, 'Test User')

    def test_get_display_name_username_only(self):
        """Test get_display_name returns username when no full name"""
        name = BaseNotificationService.get_display_name(self.user_username_only)
        self.assertEqual(name, 'usernameonly')

    def test_get_display_name_none_user(self):
        """Test get_display_name with None user uses fallback"""
        name = BaseNotificationService.get_display_name(None)
        self.assertEqual(name, 'User')

    def test_get_display_name_custom_fallback(self):
        """Test get_display_name with custom fallback"""
        name = BaseNotificationService.get_display_name(None, 'Instructor')
        self.assertEqual(name, 'Instructor')

    def test_get_display_name_empty_full_name(self):
        """Test get_display_name when get_full_name returns empty string"""
        user = User.objects.create_user(username='emptyname')
        user.first_name = ''
        user.last_name = ''
        user.save()

        name = BaseNotificationService.get_display_name(user)
        self.assertEqual(name, 'emptyname')  # Falls back to username


class BaseNotificationServiceIntegrationTestCase(TestCase):
    """Integration tests showing how utility methods work together"""

    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            username='integration_user',
            email='integration@example.com',
            first_name='Integration',
            last_name='Test'
        )
        # Profile is auto-created by signal, just retrieve and update it
        self.profile = self.user.profile
        self.profile.workshop_email_notifications = True
        self.profile.save()

    def test_typical_notification_flow(self):
        """Test typical notification method flow using utilities"""
        # 1. Validate email
        is_valid, email = BaseNotificationService.validate_email(self.user, 'Student')
        self.assertTrue(is_valid)

        # 2. Check opt-out
        should_send = BaseNotificationService.check_opt_out(
            self.user,
            'workshop_email_notifications'
        )
        self.assertTrue(should_send)

        # 3. Get display name
        display_name = BaseNotificationService.get_display_name(self.user)
        self.assertEqual(display_name, 'Integration Test')

        # All checks passed - ready to send notification
        self.assertTrue(is_valid and should_send)
