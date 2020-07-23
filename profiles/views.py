import requests
import os
import sys
from datetime import timedelta

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import gettext as _
from django.views.generic import (
    FormView,
    ListView,
    DeleteView,
    TemplateView,
    DetailView,
)
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.decorators import otp_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.expressions import RawSQL
from django.utils import timezone


from invitations.models import Invitation

from .models import HealthcareUser
from .mixins import (
    IsAdminMixin,
    ProvinceAdminDeleteMixin,
    Is2FAMixin,
    ProvinceAdminManageMixin,
)
from .forms import (
    SignupForm,
    Healthcare2FAForm,
    HealthcareInviteForm,
    Resend2FACodeForm,
)
from .utils import get_site_name


class SignUpView(FormView):
    form_class = SignupForm
    template_name = "profiles/signup.html"
    success_url = reverse_lazy("start")

    def get(self, request, *args, **kwargs):
        invited_email = self.request.session.get("account_verified_email", None)

        # redirect to login page if there's no invited email in the session
        if not invited_email:
            messages.warning(self.request, _("No invited email in session"))
            return redirect("login")

        # redirect to login page if there's no Invitation for this email
        if not Invitation.objects.filter(email__iexact=invited_email):
            messages.error(
                self.request, "Invitation not found for {}".format(invited_email)
            )
            return redirect("login")

        return super().get(request, *args, **kwargs)

    def get_initial(self):
        invited_email = self.request.session.get("account_verified_email", None)

        # get invite object and the admin user who sent the invite
        inviter_id = Invitation.objects.get(email__iexact=invited_email).inviter_id
        inviter = HealthcareUser.objects.get(id=inviter_id)

        # preload the signup form with the email and the province of the admin
        return {
            "email": invited_email,
            "province": inviter.province.abbr,
        }

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Account created successfully"))
        return super(SignUpView, self).form_valid(form)


class Login2FAView(LoginRequiredMixin, FormView):
    form_class = Healthcare2FAForm
    template_name = "profiles/2fa.html"
    success_url = reverse_lazy("start")

    def get(self, request, *args, **kwargs):
        if request.user.is_verified():
            return redirect(reverse_lazy("start"))
        return super().get(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if settings.DEBUG:
            sms_device = self.request.user.notifysmsdevice_set.last()
            initial["code"] = sms_device.token
        return initial

    def form_valid(self, form):
        code = form.cleaned_data.get("code")
        devices = self.request.user.notifysmsdevice_set.all()
        for device in devices:
            if device.verify_token(code):
                self.request.user.otp_device = device
                self.request.session[DEVICE_ID_SESSION_KEY] = device.persistent_id

        # Using the first device, since we don't care which it is, let's
        # check if the user is being throttled
        if devices[0]:
            verified_allowed, _ = devices[0].verify_is_allowed()
            if verified_allowed is False:
                form.add_error("code", "Please try again later.")

        if self.request.user.otp_device is None and form.has_error("code") is False:
            form.add_error("code", _("That didn’t match the code that was sent."))

        if form.has_error("code"):
            return super().form_invalid(form)

        return super().form_valid(form)


class Resend2FAView(LoginRequiredMixin, FormView):
    form_class = Resend2FACodeForm
    template_name = "profiles/2fa-resend.html"
    success_url = reverse_lazy("login-2fa")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        is_valid = super().form_valid(form)
        if is_valid:
            messages.success(self.request, _("Security code has been sent."))

        return is_valid


class InvitationView(Is2FAMixin, IsAdminMixin, FormView):
    form_class = HealthcareInviteForm
    template_name = "invitations/templates/invite.html"
    success_url = reverse_lazy("invite_complete")

    def form_valid(self, form):
        # Pass user to invite, save the invite to the DB, and return it
        invite = form.save(user=self.request.user)
        current_site = get_current_site(self.request)
        subject_line = "{}{}".format(
            get_site_name(self.request), _(": Your portal account")
        )
        invite.send_invitation(
            self.request,
            scheme=self.request.scheme,
            http_host=current_site.domain,
            subject_line=subject_line,
        )
        messages.success(
            self.request, "Invitation sent to “{}”".format(invite.email), "invite"
        )
        self.request.session["invite_email"] = invite.email
        return super().form_valid(form)


class InvitationListView(Is2FAMixin, IsAdminMixin, ListView):
    template_name = "invitations/templates/invite_list.html"

    def get_queryset(self):
        return Invitation.objects.filter(
            inviter__province=self.request.user.province, accepted=False
        ).order_by("-sent")


class InvitationDeleteView(Is2FAMixin, IsAdminMixin, DeleteView):
    model = Invitation
    context_object_name = "invitation"
    success_url = reverse_lazy("invitation_list")
    template_name = "invitations/templates/invitation_confirm_delete.html"


class InvitationCompleteView(Is2FAMixin, IsAdminMixin, TemplateView):
    template_name = "invitations/templates/invite_complete.html"


class ProfilesView(Is2FAMixin, IsAdminMixin, ListView):
    def get_queryset(self):
        return (
            HealthcareUser.objects.filter(province=self.request.user.province)
            .annotate(
                current_user_email=RawSQL("email = %s", (self.request.user.email,))
            )
            .order_by("-current_user_email", "-is_admin")
        )


class UserProfileView(Is2FAMixin, ProvinceAdminManageMixin, DetailView):
    model = HealthcareUser


class UserDeleteView(Is2FAMixin, ProvinceAdminDeleteMixin, DeleteView):
    model = HealthcareUser
    context_object_name = "profile_user"
    success_url = reverse_lazy("profiles")


@login_required
@otp_required
def code(request):
    token = os.getenv("API_AUTHORIZATION")

    diagnosis_code = "000 000 0000"

    if token:
        try:
            r = requests.post(
                os.getenv("API_ENDPOINT"), headers={"Authorization": "Bearer " + token}
            )
            r.raise_for_status()  # If we don't get a valid response, throw an exception
            diagnosis_code = r.text
        except requests.exceptions.HTTPError as err:
            sys.stderr.write("Received " + str(r.status_code) + " " + err.response.text)
            sys.stderr.flush()
        except requests.exceptions.RequestException as err:
            sys.stderr.write("Something went wrong", err)
            sys.stderr.flush()

    # Split up the code with a space in the middle so it looks like this: 123 456 789
    diagnosis_code = (
        f"{diagnosis_code[0:3]} {diagnosis_code[4:7]} {diagnosis_code[8:12]}"
    )
    expiry = timezone.now() + timedelta(days=1)

    template_name = "key_instructions" if "/key-instructions" in request.path else "key"

    return render(
        request,
        "profiles/{}.html".format(template_name),
        {"code": diagnosis_code, "expiry": expiry},
    )
