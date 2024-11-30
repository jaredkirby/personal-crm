import typing
from datetime import datetime, timedelta
from enum import Enum

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Count, Index
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

LAST_INTERACTION_DEFAULT: datetime = datetime.now().astimezone() - timedelta(days=365)

CONTACT_FREQUENCY_DEFAULT: typing.Optional[int] = None


class ContactStatus(Enum):
    HIDDEN = -1
    IN_TOUCH = 1
    OUT_OF_TOUCH = 2


class Contact(models.Model):
    """
    A user's contact.
    """

    name: str = models.CharField(max_length=50)
    frequency_in_days: typing.Optional[int] = models.IntegerField(null=True, blank=True)
    user: User = models.ForeignKey(User, models.CASCADE)

    # contact details
    description: typing.Optional[str] = models.TextField(null=True, blank=True)
    linkedin_url: typing.Optional[str] = models.URLField(
        max_length=100, null=True, blank=True
    )
    twitter_url: typing.Optional[str] = models.URLField(
        max_length=100, null=True, blank=True
    )

    def get_last_interaction(self) -> typing.Optional["Interaction"]:
        return self.interactions.order_by("-was_at").first()

    def get_last_interaction_date_or_default(self) -> datetime:
        li = self.get_last_interaction()
        lid = LAST_INTERACTION_DEFAULT
        if li:
            lid = li.was_at
        return lid

    def get_urgency(self) -> int:
        """
        Gets integer-based urgency to contact. Higher is more urgent.
        :return:
        """
        if not self.frequency_in_days:
            return 0

        last_interaction_date = self.get_last_interaction_date_or_default()
        time_since_interaction = datetime.now().astimezone() - last_interaction_date
        return time_since_interaction.days - self.frequency_in_days

    def get_due_date(self) -> typing.Optional[datetime]:
        if not self.frequency_in_days:
            return None

        last_interaction_date = self.get_last_interaction_date_or_default()
        return last_interaction_date + timedelta(days=self.frequency_in_days)

    def get_status(self) -> ContactStatus:
        if not self.frequency_in_days:
            return ContactStatus.HIDDEN

        if self.get_urgency() > 0:
            return ContactStatus.OUT_OF_TOUCH
        return ContactStatus.IN_TOUCH

    def get_absolute_url(self) -> str:
        return reverse("networking_web:contact-view", kwargs={"pk": self.id})

    def __str__(self) -> str:
        return self.name


class ContactDuplicate(models.Model):
    """
    A potential duplicate.
    """

    contact: Contact = models.ForeignKey(Contact, models.CASCADE, related_name="+")
    other_contact: Contact = models.ForeignKey(
        Contact, models.CASCADE, related_name="+"
    )
    similarity: float = models.FloatField()


class EmailAddress(models.Model):
    """
    A contact's email address.
    """

    contact: Contact = models.ForeignKey(
        Contact, models.CASCADE, related_name="email_addresses"
    )
    email: str = models.EmailField(max_length=100)

    class Meta:
        unique_together = ("contact", "email")


class PhoneNumber(models.Model):
    """
    A contact's phone number.
    """

    contact: Contact = models.ForeignKey(
        Contact, models.CASCADE, related_name="phone_numbers"
    )
    phone_number: str = models.CharField(max_length=50)


class InteractionType(models.Model):
    """
    The type of interaction.
    """

    slug: str = models.SlugField()
    name: str = models.CharField(max_length=50)
    description: str = models.CharField(max_length=250)


class Interaction(models.Model):
    """
    An interaction with a specific contact.
    """

    user: User = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="interactions"
    )
    contacts: typing.List[Contact] = models.ManyToManyField(
        Contact, related_name="interactions"
    )
    type: typing.Optional[InteractionType] = models.ForeignKey(
        InteractionType, models.SET_NULL, blank=True, null=True
    )

    title: str = models.CharField(max_length=100)
    description: str = models.TextField()
    was_at: datetime = models.DateTimeField()
    # is_outgoing = models.BooleanField()

    def __str__(self) -> str:
        return f"{self.user}: {self.title} at {self.was_at}"


#
# Anthropic
#


class InteractionAnalysis(models.Model):
    """
    Stores AI-powered analysis of interactions using Claude.
    This model maintains a one-to-one relationship with Interaction,
    allowing us to store rich analytical data without cluttering the
    main Interaction model.
    """

    # Core relationship - each analysis belongs to exactly one interaction
    interaction: Interaction = models.OneToOneField(
        "Interaction",
        on_delete=models.CASCADE,
        related_name="analysis",
        help_text=_("The interaction this analysis belongs to"),
    )

    # Analysis content
    topics_discussed: typing.List[str] = models.JSONField(
        default=list, help_text=_("List of main topics identified in the interaction")
    )

    action_items: typing.List[str] = models.JSONField(
        default=list, help_text=_("List of action items extracted from the interaction")
    )

    key_insights: typing.List[str] = models.JSONField(
        default=list, help_text=_("Important points and insights from the interaction")
    )

    sentiment_score: typing.Optional[float] = models.FloatField(
        null=True, help_text=_("Sentiment score between -1 and 1")
    )

    follow_up_needed: bool = models.BooleanField(
        default=False, help_text=_("Indicates if this interaction needs follow-up")
    )

    suggested_follow_up_date: typing.Optional[datetime] = models.DateTimeField(
        null=True, blank=True, help_text=_("Recommended date for following up")
    )

    # Additional context
    personal_info_mentioned: typing.Dict[str, str] = models.JSONField(
        default=dict,
        help_text=_("Personal information mentioned during the interaction"),
    )

    conversation_context: typing.Optional[str] = models.TextField(
        null=True,
        blank=True,
        help_text=_(
            "Summary of how this interaction fits into the overall relationship"
        ),
    )

    # Metadata
    created_at: datetime = models.DateTimeField(
        auto_now_add=True, help_text=_("When this analysis was created")
    )

    last_updated: datetime = models.DateTimeField(
        auto_now=True, help_text=_("When this analysis was last updated")
    )

    analysis_version: str = models.CharField(
        max_length=50, help_text=_("Version of the analysis model used")
    )

    def get_sentiment_percentage(self) -> float:
        """
        Convert the sentiment score (-1 to 1) to a percentage (0 to 100).
        """
        if self.sentiment_score is None:
            return 50.0  # Default to neutral
        return (self.sentiment_score + 1) * 50

    def get_sentiment_category(self) -> str:
        """
        Get a categorical representation of the sentiment.
        """
        percentage = self.get_sentiment_percentage()
        if percentage > 60:
            return "positive"
        if percentage < 40:
            return "negative"
        return "neutral"

    def get_sentiment_label(self) -> str:
        """
        Get a human-readable label for the sentiment.
        """
        category = self.get_sentiment_category()
        labels = {
            "positive": "Positive",
            "negative": "Needs Attention",
            "neutral": "Neutral",
        }
        return labels[category]

    class Meta:
        verbose_name = _("interaction analysis")
        verbose_name_plural = _("interaction analyses")

        # Add indexes for frequently accessed fields
        indexes = [
            # Index for finding analyses by follow-up date
            models.Index(
                fields=["suggested_follow_up_date"], name="analysis_followup_idx"
            ),
            # Index for filtering by follow-up needed
            models.Index(
                fields=["follow_up_needed"], name="analysis_needsfollowup_idx"
            ),
            # Composite index for finding analyses within a date range
            models.Index(
                fields=["created_at", "last_updated"], name="analysis_dates_idx"
            ),
            # Index for sentiment queries
            models.Index(fields=["sentiment_score"], name="analysis_sentiment_idx"),
        ]

    def __str__(self) -> str:
        """String representation of the analysis"""
        return f"Analysis of {self.interaction} (Created: {self.created_at.date()})"


#
# Google
#


class GoogleEmail(models.Model):
    # link to social account and delete if social account gets deleted
    social_account: SocialAccount = models.ForeignKey(SocialAccount, models.CASCADE)

    # link to created interaction (if any)
    interaction: typing.Optional[Interaction] = models.ForeignKey(
        Interaction, models.SET_NULL, "google_emails", null=True
    )

    gmail_message_id: str = models.CharField(max_length=100)
    data: typing.Dict[str, typing.Any] = models.JSONField()


class GoogleCalendarEvent(models.Model):
    # link to social account and delete if social account gets deleted
    social_account: SocialAccount = models.ForeignKey(SocialAccount, models.CASCADE)

    # link to created interaction (if any)
    interaction: typing.Optional[Interaction] = models.ForeignKey(
        Interaction, models.SET_NULL, "google_calendar_events", null=True
    )

    # google id
    google_calendar_id: str = models.CharField(max_length=100)

    # data
    data: typing.Dict[str, typing.Any] = models.JSONField()


#
# helpers
#


def get_recent_contacts(
    user: User, limit: int = 5, timespan_days: int = 14
) -> typing.List[Contact]:
    """
    Fetch contacts recently interacted with.
    :param user: user
    :param limit: limit
    :param timespan_days: definition of recent in days
    :return: recent contacts
    """
    timespan_recent = datetime.now().astimezone() - timedelta(days=timespan_days)
    contacts_recent = (
        Contact.objects.filter(interactions__was_at__gt=timespan_recent)
        .filter(user=user)
        .annotate(count=Count("interactions"))
        .order_by("-count")[:limit]
    )
    return list(contacts_recent)


def get_frequent_contacts(user: User, limit: int = 5) -> typing.List[Contact]:
    """
    Fetch contacts with frequent interactions.
    :param user: user
    :param limit: limit
    :return: frequent contacts
    """
    contacts_frequent = (
        Contact.objects.filter(user=user)
        .annotate(count=Count("interactions"))
        .order_by("-count")[:limit]
    )
    return list(contacts_frequent)


def get_due_contacts(user: User) -> typing.List[Contact]:
    """
    Fetch due contacts and sort by urgency (desc).
    :param user: user
    :return: due contacts
    """
    contacts = (
        Contact.objects.filter(user=user)
        .order_by("name")
        .prefetch_related("interactions")
        .all()
    )
    contacts = filter(lambda c: c.get_urgency() > 0, contacts)
    contacts = sorted(contacts, key=lambda c: c.get_urgency(), reverse=True)
    return list(contacts)


def get_or_create_contact_email(email: str, user: User) -> EmailAddress:
    """
    Get or create an email address object.

    :param email: raw email
    :param user: owning user
    :return: existing or created email address
    """
    email_clean = clean_email(email)
    ea = EmailAddress.objects.filter(email=email_clean, contact__user=user).first()
    if not ea:
        # email does not exist
        # -> create contact (dummy) and email
        contact = Contact.objects.create(
            user=user, name=email, frequency_in_days=CONTACT_FREQUENCY_DEFAULT
        )
        ea = EmailAddress.objects.create(email=email_clean, contact=contact)
    return ea


def clean_email(email: str) -> str:
    """
    Clean an email address.
    :param email: input
    :return: cleaned email
    """
    return email.lower()
