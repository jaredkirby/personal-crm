from django.contrib import admin

from networking_base.models import Contact, Interaction
from .models import InteractionAnalysis

admin.site.register(Contact)
admin.site.register(Interaction)


@admin.register(InteractionAnalysis)
class InteractionAnalysisAdmin(admin.ModelAdmin):
    """Admin interface for interaction analyses"""

    list_display = (
        "interaction",
        "sentiment_score",
        "follow_up_needed",
        "suggested_follow_up_date",
        "created_at",
    )
    list_filter = ("follow_up_needed", "analysis_version")
    search_fields = ("interaction__title", "conversation_context")
    readonly_fields = ("created_at", "last_updated")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "interaction",
                    "sentiment_score",
                    "follow_up_needed",
                    "suggested_follow_up_date",
                )
            },
        ),
        (
            "Analysis Content",
            {
                "fields": (
                    "topics_discussed",
                    "action_items",
                    "key_insights",
                    "personal_info_mentioned",
                    "conversation_context",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("analysis_version", "created_at", "last_updated"),
                "classes": ("collapse",),
            },
        ),
    )
