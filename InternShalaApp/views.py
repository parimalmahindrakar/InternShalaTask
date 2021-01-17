from django.shortcuts import render, HttpResponseRedirect, redirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMessage
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from django.views.generic import View
from django.utils.encoding import force_bytes, force_text, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.template.loader import render_to_string
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.template import RequestContext
from .forms import CreateUserForm, TakeReviewForm
from .utils import token_generator
import re
import json
from django.http import JsonResponse
from .models import TakeReview


@login_required(login_url="login")
def home(request):
    all_reviews = TakeReview.objects.all()
    
    return render(request, "InternShalaApp/home.html", {"all_reviews": all_reviews})


def add_review(request):
    data = json.loads(request.body)
    print(data)
    review = data['actual_review']
    user = data['user']
    email = data['email']
    print("this is the fucking email \n\n\n\n\n\n",email)
    TakeReview.objects.create(user=user, email=email, review=review)
    return JsonResponse({"msg": "added data"})


def loginPage(request):
    if request.user.is_authenticated:
        return redirect("home")
    else:
        if request.method == "POST":
            user = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(request, username=user, password=password)
            if user is not None:
                login(request, user)
                return redirect("home")
            else:
                messages.info(request, "username or password is incorrect.")
                return redirect("login")

        return render(request, "InternShalaApp/login.html")


def logoutPage(request):
    logout(request)
    return redirect("login")


def signupForm(request):
    form = CreateUserForm()
    if request.method == "POST":
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_active = False
            user.save()

            username = form.cleaned_data.get("username")
            domain = get_current_site(request).domain
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            link = reverse(
                "activate_email",
                kwargs={"uidb64": uidb64,
                        "token": token_generator.make_token(user)},
            )
            activate_url = "http://"+domain+link
            email = form.cleaned_data.get("email")
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [email]
            msg = (
                "Please click following url to activate your account !\n" + activate_url
            )
            email = EmailMessage(
                "Activate your account !", msg, email_from, recipient_list
            )
            email.send()

            messages.success(
                request,
                "Account was created for "
                + username
                + ". Please verify your email id to login !",
            )
            return redirect("login")

    context = {"form": form}
    return render(request, "InternShalaApp/signup.html", {"form": form})


def activateEmailAccount(request, uidb64, token):

    try:
        id = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(id=id)
        if not token_generator.check_token(user, token):
            return redirect("login")
        if user.is_active:
            return redirect("login")
        user.is_active = True
        user.save()
        messages.success(request, "Account activated successfully !")
        return redirect("login")
    except:
        pass
    return redirect("login")


def validate_email(email):
    if len(email) > 6:
        if re.match("\b[\w\.-]+@[\w\.-]+\.\w{2,4}\b", email) != None:
            return True
    return False


class RequestResetPasswordView(View):
    def get(self, request):
        return render(request, "password_reset/request_reset_email.html")

    def post(self, request):
        email = request.POST.get("email")
        if validate_email(email):
            messages.error(request, "Please enter the valid emailid")
            return render(request, "password_reset/request_reset_email.html")
        user = User.objects.filter(email=email)

        if user.exists():
            user = user[0]
            current_site = get_current_site(request)
            uidb64 = urlsafe_base64_encode(force_bytes(user.id))
            msg = render_to_string(
                "password_reset/request_reset_password.html",
                {
                    "user": user,
                    "domain": current_site.domain,
                    "uid": uidb64,
                    "token": PasswordResetTokenGenerator().make_token(user),
                },
            )

            email_from = settings.EMAIL_HOST_USER
            recipient_list = [email]

            email = EmailMessage(
                "[Reset your password]", msg, email_from, recipient_list
            )
            email.send()

            messages.success(
                request,
                "We have sent you an email with instructions on how to reset your password",
            )
            return render(request, "password_reset/request_reset_email.html")
        else:
            messages.error(
                request, "User does not exists corresponding to this email.")
            return render(request, "password_reset/request_reset_email.html")


class SetNewPasswordView(View):
    def get(self, request, uidb64, token):
        context = {"uidb64": uidb64, "token": token}
        try:
            user_id = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=user_id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                messages.info(request, "Password reset link is invalid !")
                return redirect("login")
        except:
            pass
        return render(request, "password_reset/set_new_password.html", context)

    def post(self, request, uidb64, token):
        context = {"uidb64": uidb64, "token": token}
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords don't match. Enter again !")
            return render(request, "password_reset/set_new_password.html", context)

        SpecialSym = ["$", "@", "#", "%"]
        if len(password1) < 6:
            messages.error(
                request, "You should use atlease 8 characters. Enter again !"
            )
            return render(request, "password_reset/set_new_password.html", context)

        if not any(char.isdigit() for char in password1):
            messages.error(
                request, "Password should have at least one numeral !")
            return render(request, "password_reset/set_new_password.html", context)

        if not any(char.isupper() for char in password1):
            messages.error(
                request, "Password should have at least one uppercase letter !"
            )
            return render(request, "password_reset/set_new_password.html", context)

        if not any(char.islower() for char in password1):
            messages.error(
                request, "Password should have at least one lowercase letter"
            )
            return render(request, "password_reset/set_new_password.html", context)

        if not any(char in SpecialSym for char in password1):
            messages.error(
                request, "Password should have at least one of the symbols $@#"
            )
            return render(request, "password_reset/set_new_password.html", context)

        try:
            user_id = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=user_id)
            user.set_password(password1)
            user.save()
            messages.success(request, "Password was reset.")
            return redirect("login")
        except:
            messages.error(request, "Something went wrong !")
            return render(request, "password_reset/set_new_password.html", context)
        return render(request, "password_reset/set_new_password.html", context)
