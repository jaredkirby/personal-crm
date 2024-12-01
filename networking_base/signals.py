"""
Signal handlers for the networking_base application.
These handlers manage automated tasks like interaction analysis and notification generation.
"""

import json
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from anthropic import Anthropic
import logging
from datetime import datetime, timedelta

from .models import Interaction, InteractionAnalysis
from .errors import AnalysisError

logger = logging.getLogger(__name__)


def parse_follow_up_date(date_str: str, base_datetime: datetime) -> datetime:
    """
    Parse a follow-up date string and ensure it's timezone-aware.

    Args:
        date_str: Date string in YYYY-MM-DD format
        base_datetime: Reference datetime to use for timezone information

    Returns:
        A timezone-aware datetime object
    """
    try:
        # Parse the date string into a datetime
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")

        # Create a timezone-aware datetime using the same time as the base datetime
        aware_datetime = timezone.make_aware(
            datetime.combine(date_obj.date(), base_datetime.time()),
            timezone=base_datetime.tzinfo,
        )

        return aware_datetime
    except (ValueError, TypeError) as e:
        # If parsing fails, return a default date
        logger.warning(f"Failed to parse follow-up date '{date_str}': {str(e)}")
        return base_datetime + timedelta(days=7)


@receiver(m2m_changed, sender=Interaction.contacts.through)
def analyze_new_interaction(sender, instance: Interaction, action: str, **kwargs):
    """
    Signal handler that triggers Claude analysis when contacts are added to an interaction.
    Ensures all datetime handling is timezone-aware.
    """
    if action != "post_add":
        return

    try:
        # Skip if already analyzed
        if hasattr(instance, "analysis"):
            return

        # Verify API key is available
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            logger.error("No Anthropic API key found in settings")
            raise AnalysisError("Missing Anthropic API key")

        # Initialize Anthropic client
        client = Anthropic(api_key=api_key)

        # Build context from recent interactions with these contacts
        context_parts = []
        for contact in instance.contacts.all():
            recent = contact.interactions.order_by("-was_at")[:3]
            if recent:
                context_parts.append(f"\nRecent interactions with {contact.name}:")
                context_parts.extend(
                    [
                        f"- {interaction.was_at.strftime('%Y-%m-%d')}: {interaction.title}"
                        for interaction in recent
                    ]
                )

        context = (
            "\n".join(context_parts)
            if context_parts
            else "No previous interactions found."
        )

        # Create the analysis prompt with explicit JSON structure request
        prompt = f"""Analyze this interaction and provide insights in valid JSON format using this exact structure:
        {{
            "topics_discussed": ["topic1", "topic2", ...],
            "action_items": ["action1", "action2", ...],
            "key_insights": ["insight1", "insight2", ...],
            "sentiment_score": <float between -1 and 1>,
            "follow_up_needed": <boolean>,
            "suggested_follow_up_date": "<YYYY-MM-DD>",
            "personal_info_mentioned": {{"category1": "info1", "category2": "info2", ...}},
            "conversation_context": "summary of how this interaction fits into the relationship"
        }}

        Interaction to analyze:
        Title: {instance.title}
        Description: {instance.description}
        Date: {instance.was_at}
        Contacts: {', '.join(c.name for c in instance.contacts.all())}
        
        Recent Context:
        {context}"""

        # Get analysis from Claude
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract and parse the JSON response
        try:
            response_text = response.content[0].text

            # Parse JSON from markdown if present
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0]
            else:
                json_text = response_text

            # Parse the JSON data
            analysis_data = json.loads(json_text)

            # Parse the follow-up date with timezone awareness
            follow_up_date = parse_follow_up_date(
                analysis_data.get("suggested_follow_up_date"), instance.was_at
            )

            # Create the analysis record with proper timezone handling
            InteractionAnalysis.objects.create(
                interaction=instance,
                topics_discussed=analysis_data.get("topics_discussed", []),
                action_items=analysis_data.get("action_items", []),
                key_insights=analysis_data.get("key_insights", []),
                sentiment_score=analysis_data.get("sentiment_score", 0.0),
                follow_up_needed=analysis_data.get("follow_up_needed", False),
                suggested_follow_up_date=follow_up_date,
                personal_info_mentioned=analysis_data.get(
                    "personal_info_mentioned", {}
                ),
                conversation_context=analysis_data.get("conversation_context", ""),
                analysis_version="claude-3-sonnet-20240229",
            )

            logger.info(f"Successfully analyzed interaction {instance.id}")

        except json.JSONDecodeError as e:
            raise AnalysisError(
                f"Failed to parse Claude response as JSON: {str(e)}", original_error=e
            )

    except Exception as e:
        logger.error(f"Failed to analyze interaction {instance.id}: {str(e)}")
        if not isinstance(e, AnalysisError):
            e = AnalysisError(f"Analysis failed: {str(e)}", original_error=e)
        raise e
