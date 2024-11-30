from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from anthropic import Anthropic
import logging

from .models import Interaction, InteractionAnalysis

logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Custom exception for analysis failures"""

    pass


@receiver(post_save, sender=Interaction)
def analyze_new_interaction(sender, instance: Interaction, created: bool, **kwargs):
    """
    Signal handler that triggers Claude analysis when a new interaction is created.
    This runs asynchronously after the interaction is saved to the database.

    Args:
        sender: The model class (Interaction)
        instance: The actual Interaction instance that was saved
        created: Boolean indicating if this is a new instance
    """
    try:
        # Only analyze newly created interactions
        if not created:
            return

        # Initialize Anthropic client
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Prepare context from recent interactions
        recent_interactions = instance.contacts.first().interactions.order_by(
            "-was_at"
        )[:5]
        context = "\n".join(
            [
                f"- {interaction.was_at.strftime('%Y-%m-%d')}: {interaction.title}"
                for interaction in recent_interactions
            ]
        )

        # Create the analysis prompt
        prompt = f"""Please analyze this interaction and provide structured insights:

        Interaction Title: {instance.title}
        Description: {instance.description}
        Date: {instance.was_at}
        
        Recent Context with this contact:
        {context}
        
        Analyze the interaction focusing on:
        1. Main topics discussed
        2. Action items or follow-ups needed
        3. Key insights about the relationship
        4. Overall sentiment
        5. Suggested next contact date
        6. Personal information mentioned
        
        Format the response as detailed JSON suitable for database storage."""

        # Get analysis from Claude
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse the response
        analysis_data = response.content[0].text

        # Create the analysis record
        InteractionAnalysis.objects.create(
            interaction=instance,
            topics_discussed=analysis_data.get("topics_discussed", []),
            action_items=analysis_data.get("action_items", []),
            key_insights=analysis_data.get("key_insights", []),
            sentiment_score=analysis_data.get("sentiment_score"),
            follow_up_needed=analysis_data.get("follow_up_needed", False),
            suggested_follow_up_date=analysis_data.get("suggested_follow_up_date"),
            personal_info_mentioned=analysis_data.get("personal_info_mentioned", {}),
            conversation_context=analysis_data.get("conversation_context", ""),
            analysis_version="claude-3-sonnet-20240229",
        )

        logger.info(f"Successfully analyzed interaction {instance.id}")

    except Exception as e:
        logger.error(f"Failed to analyze interaction {instance.id}: {str(e)}")
        raise AnalysisError(f"Analysis failed: {str(e)}")
