from django.contrib import admin
from .models import Conversation, ConversationReadStatus, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('sender', 'content', 'created_at')
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'domain', 'participant_1', 'participant_2', 'get_context', 'created_at', 'updated_at')
    list_filter = ('domain', 'created_at')
    search_fields = ('participant_1__username', 'participant_1__email',
                     'participant_2__username', 'participant_2__email',
                     'workshop__title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [MessageInline]

    fieldsets = (
        ('Participants', {
            'fields': ('domain', 'participant_1', 'participant_2')
        }),
        ('Context', {
            'fields': ('workshop', 'child_profile')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_context(self, obj):
        """Display what this conversation is about"""
        if obj.domain == 'workshop' and obj.workshop:
            return f"Workshop: {obj.workshop.title}"
        elif obj.domain == 'private_teaching':
            if obj.child_profile:
                return f"Child: {obj.child_profile.full_name}"
            return "General"
        return "-"
    get_context.short_description = 'Context'


@admin.register(ConversationReadStatus)
class ConversationReadStatusAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'user', 'last_read_at')
    list_filter = ('last_read_at',)
    search_fields = ('user__username', 'user__email', 'conversation__id')
    readonly_fields = ('last_read_at',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_conversation_display', 'sender', 'get_content_preview', 'created_at')
    list_filter = ('created_at', 'conversation__domain')
    search_fields = ('sender__username', 'sender__email', 'content', 'conversation__id')
    readonly_fields = ('id', 'created_at')

    fieldsets = (
        ('Message', {
            'fields': ('conversation', 'sender', 'content')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def get_conversation_display(self, obj):
        """Display conversation info"""
        return f"{obj.conversation.domain}: {obj.conversation.participant_1.username} & {obj.conversation.participant_2.username}"
    get_conversation_display.short_description = 'Conversation'

    def get_content_preview(self, obj):
        """Show preview of message content"""
        return obj.content[:75] + '...' if len(obj.content) > 75 else obj.content
    get_content_preview.short_description = 'Content'
