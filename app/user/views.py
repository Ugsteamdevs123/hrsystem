from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response


from .serializers import (
    UserLoginSerializer,
)

from django.contrib.auth import login, logout
from rest_framework import status
from django.middleware.csrf import get_token
from rest_framework.permissions import AllowAny , IsAuthenticated
from rest_framework.authentication import SessionAuthentication


from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import CompanyForm , CustomUserForm

# Create your views here.


class LoginView(View):
    template_name = "login.html"

    def get(self, request):
        """
        Handles GET requests and renders the login form.
        """
        return render(request, self.template_name)

    def post(self, request):
        """
        Handles POST requests and authenticates the user.
        """
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(username=email, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("dashboard")  # Replace with your dashboard URL
            else:
                messages.error(request, "Your account is disabled.")
        else:
            messages.error(request, "Invalid email or password.")

        return render(request, self.template_name)
    


class DashboardView(View):
    template_name = "dashboard.html"

    def get(self, request):
        """
        Shows the dashboard with two buttons.
        """
        return render(request, self.template_name)


class AddCompanyView(View):
    template_name = "add_company.html"

    def get(self, request):
        form = CompanyForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Company added successfully!")
            return redirect("dashboard")
        return render(request, self.template_name, {"form": form})

class AddHRView(View):
    template_name = "add_hr.html"

    def get(self, request):
        form = CustomUserForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "HR user added successfully!")
            return redirect("dashboard")
        return render(request, self.template_name, {"form": form})



class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("login")  # Replace with your login URL name


















