import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q


class Conversation(models.Model):
    """
    Two-person conversation thread.
    Can be attached to workshop or private teaching relationship.
    """

    DOMAIN_CHOICES = [
        ('workshop', 'Workshop'),
        ('private_teaching', 'Private Teaching'),
    ]

    # Identity
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.CharField(max_length=30, choices=DOMAIN_CHOICES, db_index=True)

    # Two participants (always exactly 2)
    participant_1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations_as_p1',
        help_text="First participant in the conversation"
    )
    participant_2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations_as_p2',
        help_text="Second participant in the conversation"
    )

    # Context - what this conversation is about (use real FKs)
    workshop = models.ForeignKey(
        'workshops.Workshop',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='conversations',
        help_text="Workshop this conversation is about (if applicable)"
    )

    # For private teaching with children
    child_profile = models.ForeignKey(
        'accounts.ChildProfile',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='teaching_conversations',
        help_text="Child this conversation is about (if applicable)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['domain', '-updated_at']),
            models.Index(fields=['workshop', '-updated_at']),
        ]
        # Ensure one conversation per context
        constraints = [
            # Workshop: One conversation per participant+workshop
            models.UniqueConstraint(
                fields=['workshop', 'participant_1', 'participant_2'],
                name='unique_workshop_conversation',
                condition=Q(domain='workshop')
            ),
            # Private teaching: One conversation per teacher+student (per child if applicable)
            models.UniqueConstraint(
                fields=['participant_1', 'participant_2', 'child_profile'],
                name='unique_private_teaching_conversation',
                condition=Q(domain='private_teaching')
            ),
        ]

    def __str__(self):
        if self.domain == 'workshop' and self.workshop:
            return f"Workshop: {self.workshop.title} - {self.participant_1.get_full_name()} & {self.participant_2.get_full_name()}"
        elif self.domain == 'private_teaching':
            child_info = f" (re: {self.child_profile.full_name})" if self.child_profile else ""
            return f"Private Teaching: {self.participant_1.get_full_name()} & {self.participant_2.get_full_name()}{child_info}"
        return f"{self.domain}: {self.participant_1.username} & {self.participant_2.username}"

    def get_other_participant(self, user):
        """Get the other person in this conversation"""
        return self.participant_2 if user == self.participant_1 else self.participant_1

    def get_unread_count(self, user):
        """Get unread message count for a user"""
        last_read = self.read_status.filter(user=user).first()

        # Use Message.objects instead of self.messages to avoid issues with prefetch slicing
        messages_qs = Message.objects.filter(conversation=self)

        if not last_read:
            # Never read - count all messages not from this user
            return messages_qs.exclude(sender=user).count()
        # Count messages after last read that aren't from this user
        return messages_qs.filter(
            created_at__gt=last_read.last_read_at
        ).exclude(sender=user).count()

    def mark_as_read(self, user):
        """Mark conversation as read for a user"""
        ConversationReadStatus.objects.update_or_create(
            conversation=self,
            user=user,
            defaults={'last_read_at': models.functions.Now()}
        )

    def get_display_title(self, for_user):
        """Get display title from perspective of for_user"""
        other = self.get_other_participant(for_user)
        other_name = other.get_full_name() or other.username

        if self.domain == 'workshop' and self.workshop:
            return f"{other_name} - {self.workshop.title}"
        elif self.domain == 'private_teaching':
            if self.child_profile:
                return f"{other_name} - {self.child_profile.full_name}"
            return other_name
        return other_name


class ConversationReadStatus(models.Model):
    """Track when each participant last read the conversation"""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='read_status'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    last_read_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['conversation', 'user']
        verbose_name_plural = 'Conversation read statuses'

    def __str__(self):
        return f"{self.user.username} - {self.conversation} - {self.last_read_at}"


class Message(models.Model):
    """Individual message within a conversation"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        sender_name = self.sender.get_full_name() or self.sender.username
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{sender_name}: {preview}"
