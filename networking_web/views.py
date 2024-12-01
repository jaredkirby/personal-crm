from collections import defaultdict
from datetime import datetime
from typing import Any, Dict

# Django imports - group by functionality
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from pytz import UTC

# Local imports - group by module
from networking_base.errors import AnalysisError  # Import from new location
from networking_base.models import (
    Contact,
    ContactDuplicate,
    ContactStatus,
    EmailAddress,
    Interaction,
    InteractionAnalysis,
    get_due_contacts,
    get_frequent_contacts,
    get_recent_contacts,
)
from .forms import InteractionForm

# Constants
CONTACT_FIELDS_DEFAULT = [
    "name",
    "frequency_in_days",
    "description",
    "linkedin_url",
    "twitter_url",
]


class ContactListView(LoginRequiredMixin, ListView):
    model = Contact
    template_name = "web/_atomic/pages/contacts-overview.html"
    ordering = "name"

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(*args, **kwargs)

        contacts = context["contact_list"]
        contacts_by_status = defaultdict(list)
        for contact in contacts:
            contacts_by_status[contact.get_status()].append(contact)

        # add counts
        contact_counts = {
            "selected": len([c for c in contacts if c.frequency_in_days]),
            "out_of_touch": len(contacts_by_status.get(ContactStatus.OUT_OF_TOUCH, [])),
            "in_touch": len(contacts_by_status.get(ContactStatus.IN_TOUCH, [])),
            "hidden": len(contacts_by_status.get(ContactStatus.HIDDEN, [])),
        }
        context.update({k + "_count": v for k, v in contact_counts.items()})

        # filter status
        status = None
        status_raw = self.request.GET.get("status", None)
        if status_raw:
            # get status enum
            status = ContactStatus(int(self.request.GET.get("status")))

            # re-filter contacts
            context["contact_list"] = list(
                filter(lambda c: c.get_status() == status, contacts)
            )
        else:
            # only show selected
            context["contact_list"] = [c for c in contacts if c.frequency_in_days]

        return context


class ContactDetailView(LoginRequiredMixin, DetailView):
    model = Contact
    template_name = "web/_atomic/pages/contacts-detail.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["interactions"] = context["object"].interactions.order_by("-was_at")
        context["duplicates"] = ContactDuplicate.objects.filter(
            contact=context["object"]
        ).order_by("-similarity")
        return context


class ContactUpdateView(LoginRequiredMixin, UpdateView):
    model = Contact
    fields = CONTACT_FIELDS_DEFAULT
    template_name = "web/_atomic/pages/contacts_form.html"

    def get_success_url(self) -> str:
        return reverse("networking_web:contact-view", kwargs={"pk": self.object.id})


class ContactCreateView(LoginRequiredMixin, CreateView):
    model = Contact
    fields = CONTACT_FIELDS_DEFAULT
    template_name = "web/_atomic/pages/contacts_form.html"

    def form_valid(self, form: Any) -> HttpResponse:
        self.object = form.save(commit=False)
        self.object.user_id = self.request.user.id
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        return reverse("networking_web:contact-view", kwargs={"pk": self.object.id})


class ContactDeleteView(LoginRequiredMixin, DeleteView):
    model = Contact
    template_name = "web/_atomic/pages/contacts_confirm_delete.html"

    def get_success_url(self) -> str:
        success_url = reverse("networking_web:index")
        return success_url


class EmailDeleteView(LoginRequiredMixin, DeleteView):
    model = EmailAddress
    template_name = "web/_atomic/pages/email-confirm-delete.html"

    def get_queryset(self) -> Any:
        return EmailAddress.objects.filter(contact__user=self.request.user)

    def get_success_url(self) -> str:
        return reverse(
            "networking_web:contact-view", kwargs={"pk": self.object.contact_id}
        )


class EmailListView(LoginRequiredMixin, ListView):
    model = EmailAddress
    template_name = "web/_atomic/pages/contacts-emails-overview.html"

    def get_queryset(self) -> Any:
        return EmailAddress.objects.filter(
            contact_id=self.kwargs["pk"], contact__user=self.request.user
        )

    def get_context_data(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["contact"] = Contact.objects.get(
            id=self.kwargs["pk"], user=self.request.user
        )
        return context


class InteractionListView(LoginRequiredMixin, ListView):
    model = Interaction
    template_name = "web/_atomic/pages/interactions-overview.html"

    def get_queryset(self) -> Any:
        return Interaction.objects.filter(
            # owned by user
            user=self.request.user,
            # past interactions only
            was_at__lt=datetime.now().astimezone(),
            # of contacts that are selected
            contacts__frequency_in_days__isnull=False,
        ).order_by("-was_at")


class InteractionCreateView(LoginRequiredMixin, CreateView):
    """
    Handles creation of new interactions with automatic analysis.

    This view manages both the basic interaction creation and triggers
    the asynchronous analysis process. It provides detailed feedback
    to users about the success or failure of both operations.
    """

    model = Interaction
    form_class = InteractionForm
    template_name = "web/_atomic/pages/interactions-form.html"
    success_url = reverse_lazy("networking_web:interactions-overview")

    def form_valid(self, form):
        """
        Handle form submission with proper error handling and object lifecycle management.

        This method:
        1. Saves the basic interaction data
        2. Associates the interaction with contacts
        3. Triggers the analysis process
        4. Provides appropriate feedback to the user
        """
        try:
            # First save the interaction
            self.object = form.save(commit=False)
            self.object.user = self.request.user
            self.object.save()

            # Now save the many-to-many data
            form.save_m2m()

            messages.success(
                self.request,
                "Interaction saved successfully. Analysis will be available shortly.",
            )

            return HttpResponseRedirect(self.get_success_url())

        except AnalysisError as e:
            # Handle analysis-specific errors
            messages.warning(
                self.request, f"Interaction saved but analysis failed: {e.message}"
            )
            return HttpResponseRedirect(self.get_success_url())

        except Exception as e:
            # Handle any other unexpected errors
            messages.error(self.request, f"Error saving interaction: {str(e)}")
            return self.form_invalid(form)

    def get_success_url(self):
        """
        Determine where to redirect after successful interaction creation.

        Returns:
            str: URL to redirect to after processing
        """
        if self.object and self.object.pk:
            return reverse("networking_web:interactions-overview")
        return str(self.success_url)


class InteractionDetailView(LoginRequiredMixin, DetailView):
    model = Interaction
    template_name = "web/_atomic/pages/interactions-detail.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        try:
            analysis = self.object.analysis
            context["analysis"] = analysis

            # Add sentiment context
            context["sentiment"] = {
                "percentage": analysis.get_sentiment_percentage(),
                "category": analysis.get_sentiment_category(),
                "label": analysis.get_sentiment_label(),
            }

            # Add whether this interaction needs attention
            context["needs_attention"] = analysis.get_sentiment_category() == "negative"

        except InteractionAnalysis.DoesNotExist:
            context["analysis"] = None
            messages.info(
                self.request, "Analysis for this interaction is not available."
            )

        return context


@login_required
def index(request: HttpRequest) -> HttpResponse:
    user = request.user
    contacts = get_due_contacts(user)
    contacts_frequent = get_frequent_contacts(user)
    contacts_recent = get_recent_contacts(user)

    return render(
        request,
        "web/_atomic/pages/dashboard.html",
        {
            "contacts": contacts,
            "contacts_frequent": contacts_frequent,
            "contacts_recent": contacts_recent,
        },
    )


@login_required
def add_touchpoint(request: HttpRequest, contact_id: int) -> HttpResponse:
    contact = Contact.objects.get(pk=contact_id)
    assert contact.user == request.user
    Interaction.objects.create(
        was_at=datetime.now(tz=UTC),
        contact=contact,
        title="Interaction",
        description="...",
    )
    return redirect_back(request)


def redirect_back(request: HttpRequest) -> HttpResponse:
    referer = request.META.get("HTTP_REFERER")
    return HttpResponseRedirect(referer)
