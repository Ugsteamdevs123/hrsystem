
from rest_framework.views import APIView
from rest_framework.response import Response


from .serializers import (
    UserLoginSerializer,
)
from .models import (
    CustomUser,
    Company
)

from django.contrib.auth import login, logout
from rest_framework import status
from django.middleware.csrf import get_token
from rest_framework.permissions import AllowAny , IsAuthenticated
from rest_framework.authentication import SessionAuthentication


from django.views import View
from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import (
    CompanyForm , 
    CustomUserForm,
    CustomUserUpdateForm,

)

# Create your views here.


# class LoginView(View):
#     template_name = "login.html"

#     def get(self, request):
#         """
#         Handles GET requests and renders the login form.
#         """
#         return render(request, self.template_name)

#     def post(self, request):
#         """
#         Handles POST requests and authenticates the user.
#         """
#         email = request.POST.get("email")
#         password = request.POST.get("password")

#         user = authenticate(username=email, password=password)
#         if user is not None:
#             if user.is_active:
#                 login(request, user)
#                 return redirect("dashboard")  # Replace with your dashboard URL
#             else:
#                 messages.error(request, "Your account is disabled.")
#         else:
#             messages.error(request, "Invalid email or password.")

#         return render(request, self.template_name)


class LoginView(View):
    template_name = "login.html"

    def get(self, request):
        """Handles GET requests and renders the login form."""
        return render(request, self.template_name)

    def post(self, request):
        """Handles POST requests and authenticates only superusers."""
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(username=email, password=password)
        if user is not None:
            if user.is_active and user.is_superuser:  # ✅ check superuser
                login(request, user)
                return redirect("dashboard")  # Replace with your dashboard URL
            elif not user.is_active:
                messages.error(request, "Your account is disabled.")
            else:
                messages.error(request, "You are not authorized to access this panel.")
        else:
            messages.error(request, "Invalid email or password.")

        return render(request, self.template_name)



class DashboardView(View):
    template_name = "dashboard.html"

    def get(self, request):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect("login")

        companies = Company.objects.filter(is_deleted=False).order_by("name")
        hr_users = CustomUser.objects.filter(
            is_deleted=False,
            is_staff=True,
            is_superuser=False
        ).order_by("full_name")

        return render(request, self.template_name, {
            "companies": companies,
            "hr_users": hr_users
        })


# class DashboardView(View):
#     template_name = "dashboard.html"

#     def get(self, request):
#         """
#         Shows the dashboard with two buttons.
#         """
#         return render(request, self.template_name)


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
    

class EditCompanyView(View):
    template_name = "edit_company.html"

    def get(self, request, pk):
        company = get_object_or_404(Company, pk=pk, is_deleted=False)
        form = CompanyForm(instance=company)
        return render(request, self.template_name, {"form": form, "company": company})

    def post(self, request, pk):
        company = get_object_or_404(Company, pk=pk, is_deleted=False)
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Company updated successfully!")
            return redirect("dashboard")
        return render(request, self.template_name, {"form": form, "company": company})


class DeleteCompanyView(View):
    def get(self, request, pk):
        company = get_object_or_404(Company, pk=pk)
        company.is_deleted = True  # soft delete
        company.save()
        messages.success(request, "Company deleted successfully ")
        return redirect("dashboard")



# --- CREATE HR ---
class AddHRView(View):
    template_name = "add_hr.html"

    def get(self, request):
        form = CustomUserForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CustomUserForm(request.POST)
        if form.is_valid():
            hr = form.save(commit=False)
            hr.is_staff = True
            # Make sure HR is not admin/superuser
            hr.is_superuser = False
            hr.save()
            messages.success(request, "HR user added successfully!")
            return redirect("dashboard")
        return render(request, self.template_name, {"form": form})


# --- UPDATE HR ---
class EditHRView(View):
    template_name = "edit_hr.html"

    def get(self, request, pk):
        hr = get_object_or_404(
            CustomUser,
            pk=pk,
            is_deleted=False,
            is_staff=True,
            is_superuser=False,   # exclude superuser
        )

        print("Editing HR:", hr)

        form = CustomUserUpdateForm(instance=hr)
        return render(request, self.template_name, {"form": form, "hr": hr})

    def post(self, request, pk):
        hr = get_object_or_404(
            CustomUser,
            pk=pk,
            is_deleted=False,
            is_staff=True,
            is_superuser=False,
        )

        print("Updating HR:", hr)

        form = CustomUserUpdateForm(request.POST, instance=hr)
        if form.is_valid():
            hr = form.save(commit=False)
            hr.is_staff = True
            hr.is_superuser = False
            hr.save()
            messages.success(request, "HR user updated successfully!")
            return redirect("dashboard")
        
        else:
            print("Form errors:", form.errors)   # 👈 add this
            return render(request, self.template_name, {"form": form, "hr": hr})


# --- DELETE HR (soft delete) ---
class DeleteHRView(View):
    def get(self, request, pk):
        hr = get_object_or_404(
            CustomUser,
            pk=pk,
            is_staff=True,
            is_superuser=False,  # don’t delete superuser
        )
        hr.is_deleted = True   # soft delete
        hr.save()
        messages.success(request, "HR user deleted successfully")
        return redirect("dashboard")





# class AddHRView(View):
#     template_name = "add_hr.html"

#     def get(self, request):
#         form = CustomUserForm()
#         return render(request, self.template_name, {"form": form})

#     def post(self, request):
#         form = CustomUserForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "HR user added successfully!")
#             return redirect("dashboard")
#         return render(request, self.template_name, {"form": form})
    

# # --- UPDATE HR ---
# class EditHRView(View):
#     template_name = "edit_hr.html"

#     def get(self, request, pk):
#         hr = get_object_or_404(CustomUser, pk=pk, is_deleted=False, is_staff=False)
#         form = CustomUserForm(instance=hr)
#         return render(request, self.template_name, {"form": form, "hr": hr})

#     def post(self, request, pk):
#         hr = get_object_or_404(CustomUser, pk=pk, is_deleted=False, is_staff=False)
#         form = CustomUserForm(request.POST, instance=hr)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "HR user updated successfully!")
#             return redirect("dashboard")
#         return render(request, self.template_name, {"form": form, "hr": hr})


# # --- DELETE HR (soft delete) ---
# class DeleteHRView(View):
#     def get(self, request, pk):
#         hr = get_object_or_404(CustomUser, pk=pk, is_staff=False)
#         hr.is_deleted = True   # soft delete
#         hr.save()
#         messages.success(request, "HR user deleted successfully (soft delete).")
#         return redirect("dashboard")



class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("login")  # Replace with your login URL name


















