from django.contrib.auth.decorators import login_required , permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import View
from django.views import View
from django.core.exceptions import PermissionDenied
from django.apps import apps
from django.db import transaction, models
from django.db.models import Q, Case, When
from django.db.models.signals import post_save
from django.forms.models import model_to_dict
from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth.forms import PasswordChangeForm

from .models import (
    CustomUser,
    Company,
    Section,
    VehicleModel,
    VehicleBrand,
    hr_assigned_companies,
    DepartmentTeams,
    SummaryStatus,
    IncrementDetailsSummary,
    DynamicAttribute,
    Employee,
    Configurations,
    CurrentPackageDetails,
    ProposedPackageDetails,
    FinancialImpactPerMonth,
    DepartmentGroups,
    Designation,
    Location,
    EmployeeStatus,
    Formula,
    EmployeeDraft,
    CurrentPackageDetailsDraft,
    ProposedPackageDetailsDraft,
    FinancialImpactPerMonthDraft,
    IncrementDetailsSummaryDraft,
    FieldFormula,
    FieldReference
)

from .forms import (
    CompanyForm , 
    CustomUserForm,
    CustomUserUpdateForm,
    SectionForm,
    DepartmentGroupsForm,
    HrAssignedCompaniesForm,
    VehicleModelForm,
    ConfigurationsForm,
    FieldFormulaForm,
    FormulaForm,
    VehicleBrandForm,
    CustomPasswordChangeForm

)
from venv import logger
from permissions import PermissionRequiredMixin

from .utils import get_companies_and_department_teams, topological_sort
from .serializer import (
    IncrementDetailsSummarySerializer,
    IncrementDetailsSummaryDraftSerializer,
    DepartmentGroupsSerializer,
    DesignationSerializer,
    DesignationCreateSerializer,
    LocationsSerializer,
    EmployeeStatusSerializer,
    FieldFormulaSerializer
)

from .signals import (
    update_increment_summary_employee,
    update_increment_summary
)

import json
from decimal import Decimal
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from .signals import (
    update_increment_summary_employee,
    update_increment_summary
)
import logging


logger = logging.getLogger(__name__)


'''
When user login he redirect to pass reset
'''


class LoginView(View):
    template_name = "login.html"

    def get(self, request):
        """Handles GET requests and renders the login form."""
        return render(request, self.template_name)

    def post(self, request):
        """Handles POST requests and authenticates users."""
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(username=email, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)

                # 👇 Check if first login → redirect to password change
                if user.first_time_login_to_reset_pass == True:
                    return redirect("password_change")

                if user.is_superuser:
                    # Redirect superuser to view users page
                    return redirect("view_users")
                
                elif user.has_perm('user.can_admin_access'):
                    return redirect("view_users")
                else:
                    # Placeholder for normal users (empty page for now)
                    return redirect("hr_dashboard")
            else:
                messages.error(request, "Your account is disabled.")
        else:
            messages.error(request, "Invalid email or password.")

        return render(request, self.template_name)


class CustomPasswordChangeView(LoginRequiredMixin, View):
    template_name = "reset_password.html"   # will add below

    def get(self, request):
        form = CustomPasswordChangeForm(user=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # keep user logged in after password change
            update_session_auth_hash(request, user)

            # clear first-time flag
            request.user.first_time_login_to_reset_pass = False
            request.user.save(update_fields=["first_time_login_to_reset_pass"])

            messages.success(request, "Password changed successfully.")
            # redirect where you want after reset (dashboard or login)
            return redirect("login")  # or "dashboard" / "view_users" etc.
        else:
            messages.error(request, "Please correct the errors below.")
        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("login")  # Replace with your login URL name


# --- CREATE USER ---
class AddUserView(PermissionRequiredMixin, View):
    permission_required = "user.add_customuser"
    template_name = "add_user.html"

    def get(self, request):
        form = CustomUserForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CustomUserForm(request.POST)
        
        if form.is_valid():
            try:
                user = form.save()
                user.is_staff = True
                user.is_superuser = False
                user.save()
                hr_assigned_companies.objects.create(hr=user, company=Company.objects.all().first())
                messages.success(request, "User added successfully!")
                return redirect("view_users")
            except ValueError as e:
                # Handle validation errors from manager
                error_message = str(e)
                messages.error(request, f"Error: {error_message}")
                # Add field-specific errors
                if "Contact" in error_message:
                    form.add_error('contact', error_message)
                elif "Email" in error_message:
                    form.add_error('email', error_message)
                elif "Fullname" in error_message:
                    form.add_error('full_name', error_message)
                elif "Gender" in error_message:
                    form.add_error('gender', error_message)
        else:
            print(form.errors)
            # Convert form errors to messages for better UX
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{dict(form.fields).get(field).label}: {error}")
        
        return render(request, self.template_name, {"form": form})


# --- UPDATE USER ---
class UpdateUserView(PermissionRequiredMixin, View):
    permission_required = "user.change_customuser"
    template_name = "update_user.html"

    def get(self, request, pk):
        user = get_object_or_404(
            CustomUser,
            pk=pk,
            is_deleted=False,
            is_staff=True,
            is_superuser=False,
        )
        form = CustomUserUpdateForm(instance=user)
        return render(request, self.template_name, {"form": form, "user": user})

    def post(self, request, pk):
        user = get_object_or_404(
            CustomUser,
            pk=pk,
            is_deleted=False,
            is_staff=True,
            is_superuser=False,
        )
        form = CustomUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            user.is_staff = True
            user.is_superuser = False
            user.save()
            messages.success(request, "User updated successfully!")
            return redirect("view_users")
        return render(request, self.template_name, {"form": form, "user": user})


# --- DELETE USER (soft delete) ---
class DeleteUserView(PermissionRequiredMixin, View):
    permission_required = "user.delete_customuser"

    def get(self, request, pk):
        user = get_object_or_404(
            CustomUser,
            pk=pk,
            is_staff=True,
            is_superuser=False,
        )
        user.is_deleted = True
        user.save()
        messages.success(request, "User deleted successfully")
        return redirect("view_users")


# --- VIEW USERS ---
class ViewUsersView(PermissionRequiredMixin, View):
    permission_required = "user.view_customuser"
    template_name = "view_users.html"

    def get(self, request):
        users = CustomUser.objects.filter(
            is_staff=True,
            is_deleted=False,
            is_superuser=False
        ).select_related("gender").prefetch_related("groups")  # ✅ fetch groups too

        # attach a selected_group attribute to each user
        for user in users:
            user.selected_group = user.groups.first()  # None if no group

        return render(request, self.template_name, {"users": users})


# --- VIEW COMPANIES ---
class ViewCompaniesView(PermissionRequiredMixin, View):
    permission_required = "user.view_company"  # replace 'app' with your app name
    template_name = "view_company.html"

    def get(self, request):
        companies = Company.objects.filter(is_deleted=False)
        return render(request, self.template_name, {"companies": companies})


# --- ADD COMPANY ---
class AddCompanyView(PermissionRequiredMixin, View):
    permission_required = "user.add_company"  # 🔑 change 'app' to your app name
    template_name = "add_company.html"

    def get(self, request):
        form = CompanyForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.is_deleted = False
            company.save()
            messages.success(request, "Company added successfully!")
            return redirect("view_company")  # 🔄 go to companies list
        return render(request, self.template_name, {"form": form})


# --- UPDATE COMPANY ---
class UpdateCompanyView(PermissionRequiredMixin, View):
    permission_required = "user.change_company"
    template_name = "update_company.html"

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
            return redirect("view_company")
        return render(request, self.template_name, {"form": form, "company": company})


# --- DELETE COMPANY ---
class DeleteCompanyView(PermissionRequiredMixin, View):
    permission_required = "user.delete_company"

    def get(self, request, pk):
        company = get_object_or_404(Company, pk=pk, is_deleted=False)
        company.is_deleted = True  # ✅ soft delete only active companies
        company.save()
        messages.success(request, "Company deleted successfully!")
        return redirect("view_company")


# --- VIEW SECTIONS ---
class ViewSectionsView(PermissionRequiredMixin, View):
    permission_required = "user.view_section"  # replace 'app' with your app name
    template_name = "view_section.html"

    def get(self, request):
        company_data = get_companies_and_department_teams(request.user)
        sections = Section.objects.filter(is_deleted=False)
        return render(request, self.template_name, {"sections": sections, "company_data": company_data})


# --- ADD SECTION ---
class AddSectionView(PermissionRequiredMixin, View):
    permission_required = "user.add_section"
    template_name = "add_section.html"

    def get(self, request):
        company_data = get_companies_and_department_teams(request.user)
        form = SectionForm()
        return render(request, self.template_name, {"form": form, "company_data": company_data})

    def post(self, request):
        form = SectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.is_deleted = False
            section.save()
            messages.success(request, "Section added successfully!")
            return redirect("view_section")  # 🔄 go to sections list
        return render(request, self.template_name, {"form": form})


# --- UPDATE SECTION ---
class UpdateSectionView(PermissionRequiredMixin, View):
    permission_required = "user.change_section"
    template_name = "update_section.html"

    def get(self, request, pk):
        company_data = get_companies_and_department_teams(request.user)
        section = get_object_or_404(Section, pk=pk, is_deleted=False)
        form = SectionForm(instance=section)
        return render(request, self.template_name, {"form": form, "section": section, "company_data": company_data})

    def post(self, request, pk):
        section = get_object_or_404(Section, pk=pk, is_deleted=False)
        form = SectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, "Section updated successfully!")
            return redirect("view_section")
        return render(request, self.template_name, {"form": form, "section": section})


# --- DELETE SECTION ---
class DeleteSectionView(PermissionRequiredMixin, View):
    permission_required = "user.delete_section"

    def get(self, request, pk):
        section = get_object_or_404(Section, pk=pk, is_deleted=False)
        section.is_deleted = True  # ✅ soft delete only active sections
        section.save()
        messages.success(request, "Section deleted successfully!")
        return redirect("view_section")


# --- VIEW DEPARTMENT GROUPS ---
class ViewDepartmentGroupsView(PermissionRequiredMixin, View):
    permission_required = "user.view_departmentgroups"
    template_name = "view_departmentgroups.html"

    def get(self, request):
        company_data = get_companies_and_department_teams(request.user)
        groups = DepartmentGroups.objects.filter(is_deleted=False)
        return render(request, self.template_name, {"groups": groups, "company_data": company_data})


# --- ADD DEPARTMENT GROUP ---
class AddDepartmentGroupView(PermissionRequiredMixin, View):
    permission_required = "user.add_departmentgroups"
    template_name = "add_departmentgroups.html"

    def get(self, request):
        company_data = get_companies_and_department_teams(request.user)
        form = DepartmentGroupsForm()
        return render(request, self.template_name, {"form": form, "company_data": company_data})

    def post(self, request):
        form = DepartmentGroupsForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.is_deleted = False
            group.save()
            messages.success(request, "Department Group added successfully!")
            return redirect("view_departmentgroups")
        return render(request, self.template_name, {"form": form})


# --- UPDATE DEPARTMENT GROUP ---
class UpdateDepartmentGroupView(PermissionRequiredMixin, View):
    permission_required = "user.change_departmentgroups"
    template_name = "update_departmentgroups.html"

    def get(self, request, pk):
        company_data = get_companies_and_department_teams(request.user)
        group = get_object_or_404(DepartmentGroups, pk=pk, is_deleted=False)
        form = DepartmentGroupsForm(instance=group)
        return render(request, self.template_name, {"form": form, "group": group, "company_data": company_data})

    def post(self, request, pk):
        group = get_object_or_404(DepartmentGroups, pk=pk, is_deleted=False)
        form = DepartmentGroupsForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, "Department Group updated successfully!")
            return redirect("view_departmentgroups")
        return render(request, self.template_name, {"form": form, "group": group})


# --- DELETE DEPARTMENT GROUP ---
class DeleteDepartmentGroupView(PermissionRequiredMixin, View):
    permission_required = "user.delete_departmentgroups"

    def get(self, request, pk):
        group = get_object_or_404(DepartmentGroups, pk=pk, is_deleted=False)
        group.is_deleted = True  # soft delete
        group.save()
        messages.success(request, "Department Group deleted successfully!")
        return redirect("view_departmentgroups")


# --- VIEW HR ASSIGNED COMPANIES ---
class ViewHrAssignedCompaniesView(PermissionRequiredMixin, View):
    permission_required = "user.view_hr_assigned_companies"
    template_name = "view_hr_assigned_companies.html"

    def get(self, request):
        assignments = hr_assigned_companies.objects.filter(is_deleted=False)
        return render(request, self.template_name, {"assignments": assignments})


# --- ADD HR ASSIGNED COMPANY ---
class AddHrAssignedCompanyView(PermissionRequiredMixin, View):
    permission_required = "user.add_hr_assigned_companies"
    template_name = "add_hr_assigned_company.html"

    def get(self, request):
        form = HrAssignedCompaniesForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = HrAssignedCompaniesForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.is_deleted = False
            assignment.save()
            messages.success(request, "HR assigned company added successfully!")
            return redirect("view_hr_assigned_companies")
        return render(request, self.template_name, {"form": form})


# --- UPDATE HR ASSIGNED COMPANY ---
class UpdateHrAssignedCompanyView(PermissionRequiredMixin, View):
    permission_required = "user.change_hr_assigned_companies"
    template_name = "update_hr_assigned_company.html"

    def get(self, request, pk):
        assignment = get_object_or_404(hr_assigned_companies, pk=pk, is_deleted=False)
        form = HrAssignedCompaniesForm(instance=assignment)
        return render(request, self.template_name, {"form": form, "assignment": assignment})

    def post(self, request, pk):
        assignment = get_object_or_404(hr_assigned_companies, pk=pk, is_deleted=False)
        form = HrAssignedCompaniesForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, "HR assigned company updated successfully!")
            return redirect("view_hr_assigned_companies")
        return render(request, self.template_name, {"form": form, "assignment": assignment})


# --- DELETE HR ASSIGNED COMPANY ---
class DeleteHrAssignedCompanyView(PermissionRequiredMixin, View):
    permission_required = "user.delete_hr_assigned_companies"

    def get(self, request, pk):
        assignment = get_object_or_404(hr_assigned_companies, pk=pk, is_deleted=False)
        assignment.is_deleted = True  # soft delete
        assignment.save()
        messages.success(request, "HR assigned company deleted successfully!")
        return redirect("view_hr_assigned_companies")


# --- VIEW VEHICLES ---
class ViewVehicleListView(PermissionRequiredMixin, View):
    permission_required = "user.view_vehiclemodel"
    template_name = "view_vehicle_list.html"

    def get(self, request):
        vehicles = VehicleModel.objects.select_related("brand").all()
        return render(request, self.template_name, {"vehicles": vehicles})


# --- ADD VEHICLE ---
class AddVehicleView(PermissionRequiredMixin, View):
    permission_required = "user.add_vehiclemodel"
    template_name = "add_vehicle.html"

    def get(self, request):
        form = VehicleModelForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = VehicleModelForm(request.POST)
        if form.is_valid():
            vehicle = form.save()
            messages.success(request, "Vehicle added successfully!")
            return redirect("view_vehicles")
        return render(request, self.template_name, {"form": form})


# --- UPDATE VEHICLE ---
class UpdateVehicleView(PermissionRequiredMixin, View):
    permission_required = "user.change_vehiclemodel"
    template_name = "update_vehicle.html"

    def get(self, request, pk):
        vehicle = get_object_or_404(VehicleModel, pk=pk)
        form = VehicleModelForm(instance=vehicle)
        return render(request, self.template_name, {"form": form, "vehicle": vehicle})

    def post(self, request, pk):
        vehicle = get_object_or_404(VehicleModel, pk=pk)
        form = VehicleModelForm(request.POST, instance=vehicle)
        brand_option = request.POST.get('brand_option')
        new_brand_name = request.POST.get('new_brand')

        if form.is_valid():
            vehicle = form.save(commit=False)
            if brand_option == 'new' and new_brand_name:
                # Create new brand if it doesn't exist
                brand, created = VehicleBrand.objects.get_or_create(name=new_brand_name.strip())
                vehicle.brand = brand
            vehicle.save()
            messages.success(request, "Vehicle updated successfully!")
            return redirect("view_vehicles")
        return render(request, self.template_name, {"form": form, "vehicle": vehicle})


# --- DELETE VEHICLE ---
class DeleteVehicleView(PermissionRequiredMixin, View):
    permission_required = "user.delete_vehiclemodel"

    def get(self, request, pk):
        vehicle = get_object_or_404(VehicleModel, pk=pk)
        vehicle.delete()
        messages.success(request, "Vehicle deleted successfully!")
        return redirect("view_vehicles")


# --- ADD/EDIT BRAND ---
class AddVehicleBrandView(PermissionRequiredMixin, View):
    permission_required = ("user.add_vehiclebrand", "user.change_vehiclebrand")
    template_name = "add_vehicle_brand.html"

    def get(self, request, pk=None):
        if pk:
            brand = get_object_or_404(VehicleBrand, pk=pk)
            form = VehicleBrandForm(instance=brand)
        else:
            form = VehicleBrandForm()
        brands = VehicleBrand.objects.all()
        return render(request, self.template_name, {"form": form, "brands": brands})

    def post(self, request, pk=None):
        if pk:
            brand = get_object_or_404(VehicleBrand, pk=pk)
            form = VehicleBrandForm(request.POST, instance=brand)
        else:
            form = VehicleBrandForm(request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request, f"Brand {'updated' if pk else 'added'} successfully!")
            return redirect("add_vehicle_brand")
        brands = VehicleBrand.objects.all()
        return render(request, self.template_name, {"form": form, "brands": brands})


# --- DELETE BRAND ---
class DeleteVehicleBrandView(PermissionRequiredMixin, View):
    permission_required = "user.delete_vehiclebrand"

    def get(self, request, pk):
        brand = get_object_or_404(VehicleBrand, pk=pk)
        if VehicleModel.objects.filter(brand=brand).exists():
            messages.error(request, "Cannot delete brand because it is associated with vehicles.")
            return redirect("add_vehicle_brand")
        brand.delete()
        messages.success(request, "Brand deleted successfully!")
        return redirect("add_vehicle_brand")


# Hr login then show this dashboard view . this is incrementdetailssummary model
class HrDashboardView(PermissionRequiredMixin, View):
    """
    Class-based view for HR dashboard.
    Handles PATCH requests to update 'eligible_for_increment' value.
    Renders HR dashboard page for GET requests.
    """
    permission_required = 'user.view_incrementdetailssummary'  # ✅ set permission
    raise_exception = True  # ✅ raise 403 if no permission

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view
    
    def get(self, request):
        # Fetch companies assigned to the logged-in HR

        company_data = get_companies_and_department_teams(request.user)
            
        company_id = Company.objects.values_list('id', flat=True).first()
        if not company_id:
            return JsonResponse({'error': 'No company ID provided'}, status=400)
        try:
            # Get draft data
            increment_details_summary_draft = IncrementDetailsSummaryDraft.objects.filter(company__id=company_id)
            if increment_details_summary_draft.exists():
                data_draft = IncrementDetailsSummaryDraftSerializer(increment_details_summary_draft, many=True).data
            else:
                data_draft = []
            
            print(data_draft)
            # Get confirmed data (exclude ones already covered by draft)
            draft_department_team_ids = increment_details_summary_draft.values_list("department_team_id", flat=True)

            increment_details_summary = IncrementDetailsSummary.objects.filter(company__id=company_id).exclude(
                department_team__in=draft_department_team_ids
            )

            if increment_details_summary.exists():
                data = IncrementDetailsSummarySerializer(increment_details_summary, many=True).data
            else:
                # create a dict with all serializer fields set to None
                # fields = IncrementDetailsSummarySerializer().get_fields().keys()
                data = []
            
            # Fetch summary status (1 per company ideally)
            summary_status = SummaryStatus.objects.filter(summary_submitted=False).first()
            
            return render(request, 'hr_dashboard.html',{
                'data': list(data_draft)+list(data),
                'company_data': company_data,
                "summary_status": {
                    "id": summary_status.id,
                    "approved": summary_status.approved,
                    "summary_submitted": summary_status.summary_submitted,
                } if summary_status else None
            })
        except DepartmentTeams.DoesNotExist:
            return JsonResponse({'data': []})

        # logger.info(f"User {request.user.username} accessed HR dashboard with {len(company_data)} companies")
        # return render(request, 'hr_dashboard.html', {'company_data': company_data})

    def patch(self, request):
        # Handle AJAX PATCH request to update eligible_for_increment
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                print(data)
                summary_id = data.get('id')
                eligible_for_increment = data.get('eligible_for_increment')
                if not summary_id or not eligible_for_increment:
                    return JsonResponse({'error': 'Invalid data'}, status=400)
                summary = IncrementDetailsSummary.objects.get(id=summary_id, company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company'))

                 # Permission check
                if not request.user.has_perm('user.change_incrementdetailssummary'):
                    return JsonResponse({'error': 'Permission denied'}, status=403)
                
                summary.eligible_for_increment = int(eligible_for_increment)
                summary.save()
                return JsonResponse({'message': 'Updated successfully'})
            except (IncrementDetailsSummary.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid ID or value'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)


class HrUpdateApprovedView(PermissionRequiredMixin, View):
    """
    Class-based view for HR dashboard.
    Handles PATCH requests to update 'eligible_for_increment' value.
    Renders HR dashboard page for GET requests.
    """
    permission_required = 'user.view_incrementdetailssummary'  # ✅ set permission
    raise_exception = True  # ✅ raise 403 if no permission

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view
    
    # @csrf_exempt
    def patch(self, request):
        if request.method == "PATCH" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
            try:
                data = json.loads(request.body)
                print(data)
                obj = IncrementDetailsSummaryDraft.objects.get(id=data["id"])
                obj.approved = data["approved"]
                obj.save(update_fields=["approved"])
                return JsonResponse({"success": True})
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)
        return JsonResponse({"error": "Invalid request"}, status=405)


class HrFinalApproveSummaryView(PermissionRequiredMixin, View):
    """
    Class-based view for HR dashboard.
    Handles PATCH requests to update 'approved status' value.
    Renders HR dashboard page for GET requests.
    """
    permission_required = 'user.view_incrementdetailssummary'  # ✅ set permission
    raise_exception = True  # ✅ raise 403 if no permission

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view
    
    # @csrf_exempt
    def patch(self, request):
        if request.method == "PATCH" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
            try:
                data = json.loads(request.body)
                status = SummaryStatus.objects.get(id=data["id"], summary_submitted=False)
                status.approved = True
                
                increment_details_summary_draft = status.incrementdetailssummarydraft_set.filter(approved=True)

                print(increment_details_summary_draft)
                companies_departments = increment_details_summary_draft.values_list("company", "department_team")

                filters = Q()
                for company, dept in companies_departments:
                    filters |= Q(company_id=company, department_team_id=dept)

                employee_drafts = EmployeeDraft.objects.filter(filters)

                for emp_draft in employee_drafts:
                    # employee
                    try:
                        employee_data = model_to_dict(emp_draft, exclude=['id','employee_draft','history','edited_fields','is_deleted'])
                        employee_data["company_id"] = employee_data.pop("company")
                        employee_data["department_team_id"] = employee_data.pop("department_team")
                        employee_data["department_group_id"] = employee_data.pop("department_group")
                        employee_data["section_id"] = employee_data.pop("section")
                        employee_data["designation_id"] = employee_data.pop("designation")
                        employee_data["location_id"] = employee_data.pop("location")
                        Employee.objects.update_or_create(
                            id=emp_draft.employee.id,
                            defaults=employee_data
                        )
                    except CurrentPackageDetailsDraft.DoesNotExist:
                        pass
                    # CurrentPackageDetails
                    try:
                        current_draft = emp_draft.currentpackagedetailsdraft
                        current_data = model_to_dict(current_draft, exclude=['id','employee_draft','history','edited_fields','is_deleted'])
                        current_data["vehicle_id"] = current_data.pop("vehicle")
                        CurrentPackageDetails.objects.update_or_create(
                            employee=emp_draft.employee,
                            defaults=current_data
                        )
                        current_draft.delete()
                    except CurrentPackageDetailsDraft.DoesNotExist:
                        pass

                    # ProposedPackageDetails
                    try:
                        proposed_draft = emp_draft.proposedpackagedetailsdraft
                        proposed_data = model_to_dict(proposed_draft, exclude=['id','employee_draft','history','edited_fields','is_deleted'])
                        proposed_data["vehicle_id"] = proposed_data.pop("vehicle")
                        ProposedPackageDetails.objects.update_or_create(
                            employee=emp_draft.employee,
                            defaults=proposed_data
                        )
                        proposed_draft.delete()
                    except ProposedPackageDetailsDraft.DoesNotExist:
                        pass

                    # FinancialImpactPerMonth
                    try:
                        financial_draft = emp_draft.financialimpactpermonthdraft
                        financial_data = model_to_dict(financial_draft, exclude=['id','employee_draft','history','edited_fields','is_deleted'])
                        financial_data["emp_status_id"] = financial_data.pop("emp_status")
                        FinancialImpactPerMonth.objects.update_or_create(
                            employee=emp_draft.employee,
                            defaults=financial_data
                        )
                        financial_draft.delete()
                    except FinancialImpactPerMonthDraft.DoesNotExist:
                        pass

                    # Finally, delete the EmployeeDraft itself
                    emp_draft.delete()
                
                for increment_details_summary_draft_single in increment_details_summary_draft:
                    increment_details_summary_draft_single.delete()

                status.save(update_fields=["approved"])
                return JsonResponse({"success": True})

            except Exception as e:
                logger.error(f"Error in final approval: {str(e)}", exc_info=True)
                return JsonResponse({'error': str(e)}, status=500)
    
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)
        return JsonResponse({"error": "Invalid request"}, status=405)


@method_decorator(login_required, name='dispatch')
class CompanyDepartmentTeamView(View):
    def get(self, request):
        company_id = request.GET.get('company_id')
        if not company_id:
            return JsonResponse({'error': 'Company ID is required'}, status=400)

        # Ensure the user has access to the company
        if not hr_assigned_companies.objects.filter(hr=request.user, company=company_id).exists():
            return JsonResponse({'error': 'Unauthorized access to this company'}, status=403)

        # Fetch DepartmentTeams for the given company_id
        try:
            departments = DepartmentTeams.objects.filter(company=company_id, is_deleted=False).values('id', 'name')
            return JsonResponse({'data': list(departments)}, status=200)
        except Exception as e:
            return JsonResponse({'error': 'Failed to fetch department teams'}, status=500)


# For dept team crud
class DepartmentTeamView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request):

        # ✅ Check permission: Can view departments
        if not request.user.has_perm('user.view_departmentteams'):
            raise PermissionDenied("You do not have permission to view departments.")

        company_data = get_companies_and_department_teams(request.user)
        
        return render(request, 'department_team.html', {'company_data': company_data})

    def post(self, request):

        # ✅ Check permission: Can add department
        if not request.user.has_perm('user.add_departmentteams'):
            raise PermissionDenied("You do not have permission to add departments.")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                company_id = request.POST.get('company_id')
                name = request.POST.get('name')
                if not company_id or not name:
                    return JsonResponse({'error': 'Company and name are required'}, status=400)
                company = Company.objects.get(id=company_id, id__in=hr_assigned_companies.objects.filter(hr=request.user).values('company'))
                DepartmentTeams.objects.create(company=company, name=name)
                print("successfully")
                return JsonResponse({'message': 'Department added successfully'})
            except (Company.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid company or data'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)

    def patch(self, request):
        # ✅ Check permission: Can change department
        if not request.user.has_perm('user.change_departmentteams'):
            raise PermissionDenied("You do not have permission to edit departments.")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body.decode("utf-8"))

                department_id = data.get('id')
                name = data.get('name').strip()
                if not department_id or not name:
                    return JsonResponse({'error': 'Department ID and name are required'}, status=400)
                department = DepartmentTeams.objects.get(
                    id=department_id,
                    company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                )
                department.name = name
                department.save()
                return JsonResponse({'message': 'Department updated successfully'})
            except (DepartmentTeams.DoesNotExist, ValueError):
                print("e1: ")
                return JsonResponse({'error': 'Invalid department or data'}, status=400)
            except Exception as e:
                print("e2: ", e)
        return JsonResponse({'error': 'Invalid request'}, status=400)

    def delete(self, request):

        # ✅ Check permission: Can delete department
        if not request.user.has_perm('user.delete_departmentteams'):
            raise PermissionDenied("You do not have permission to delete departments.")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                department_id = data.get('id')
                if not department_id:
                    return JsonResponse({'error': 'Department ID is required'}, status=400)
                department = DepartmentTeams.objects.get(
                    id=department_id,
                    company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                )
                department.delete()  # Cascades to IncrementDetailsSummary due to on_delete=models.CASCADE
                return JsonResponse({'message': 'Department deleted successfully'})
            except (DepartmentTeams.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid department'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)


# show company name with dept in dropdwon 
class GetCompaniesAndDepartmentTeamsView(PermissionRequiredMixin, View):
    """
    Class-based view for fetching companies and departments teams list assigned to HR.
    """
    # permission_classes = [GroupOrSuperuserPermission]
    # group_name = 'Hr'  # Set the group name for the permission

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        return view
    
    def get(self, request):
        try:
            data = get_companies_and_department_teams(request.user)

            return JsonResponse({'data': data})  # Return companies for add_department.html
        except Exception as e:
            print(e)
            return JsonResponse({'data': [], 'error': str(e)})


class CompanySummaryView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, company_id):
        if not hr_assigned_companies.objects.filter(hr=request.user, company_id=company_id).exists():
            return render(request, 'error.html', {'error': 'Invalid company'}, status=400)

        company_data = get_companies_and_department_teams(request.user)

        company = Company.objects.get(id=company_id)   
        increment_details_summary = IncrementDetailsSummary.objects.filter(company_id=company_id)
        if increment_details_summary.exists():
            data = IncrementDetailsSummarySerializer(increment_details_summary, many=True).data
            table_html = '<table class="table table-bordered custom-table">'
            table_html += '<thead><tr>'
            # Use serializer field names (with spaces) for headers, exclude 'id'
            headers = [key for key in data[0].keys() if key != 'id']
            for header in headers:
                table_html += f'<th class="font-weight-bold border-end">{header.title()}</th>'
            table_html += '<th class="font-weight-bold border-end">Actions</th></tr></thead><tbody>'
            for row in data:
                table_html += f'<tr data-id="{row["id"]}" data-eligible="{row["eligible for increment"] if row["eligible for increment"] is not None else ""}">'
                for header in headers:
                    table_html += f'<td class="border-end">{row[header] if row[header] is not None else ""}</td>'
                table_html += '<td class="border-end"><button class="btn btn-sm btn-primary edit-btn">Edit</button></td>'
                table_html += '</tr>'
            table_html += '</tbody></table>'
        else:
            table_html = '<p>No summary data available for this company.</p>'
        # logger.info(f"User {request.user.username} accessed summary for company {company_id}")
        return render(request, 'company_summary.html', {'company_data': company_data, 'company': company, 'table_html': table_html})

    def patch(self, request, company_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                # logger.debug(f"PATCH received: {request.POST}")
                data = json.loads(request.body)
                summary_id = data.get('id')
                eligible_for_increment = data.get('eligible_for_increment')
                if not summary_id or not eligible_for_increment:
                    return JsonResponse({'error': 'Invalid data'}, status=400)
                summary = IncrementDetailsSummary.objects.get(
                    id=summary_id,
                    company_id=company_id,
                    company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                )
                summary.eligible_for_increment = int(eligible_for_increment)
                summary.save()
                # logger.debug(f"Updated summary {summary_id}: eligible_for_increment={eligible_for_increment}")
                return JsonResponse({'message': 'Updated successfully'})
            except (IncrementDetailsSummary.DoesNotExist, ValueError):
                # logger.error(f"Error updating summary: {request.POST}")
                return JsonResponse({'error': 'Invalid ID or value'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)


class DepartmentTableView(View):
    template_name = 'dept_table_list.html'

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, department_id):
        department = DepartmentTeams.objects.filter(
            id=department_id,
            company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
        ).first()
        if not department:
            return render(request, 'error.html', {'error': 'Invalid department'}, status=400)

        company_data = get_companies_and_department_teams(request.user)
        employees = Employee.objects.filter(department_team=department, resign=False).select_related(
            'company', 'department_team', 'department_group', 'section', 'designation', 'location'
        ).prefetch_related(
            'currentpackagedetails', 'proposedpackagedetails', 'financialimpactpermonth', 'drafts'
        )

        employee_data = []
        draft_data = {}

        for emp in employees:
            emp_draft = emp.drafts.first()
            is_draft = bool(emp_draft)

            # Make sure date_of_joining exists
            if emp.date_of_joining:
                six_months_ago = date.today() - relativedelta(months=6)
                past_six_months = emp.date_of_joining <= six_months_ago
            else:
                past_six_months = False
            
            data = {}
            # for key, value in emp.__dict__:
            #     if key == "dynamic_attribute":
            #         for d_key, d_value in value:
            #             data[d_key] = d_value
            #     if key not in ["auto_mark_eligibility", "is_intern", "promoted_from_intern_date", "is_deleted", "history"]:
            #         data[key] = value
            data = {
                'emp_id': emp.emp_id,
                'past_six_months': past_six_months,
                'fullname': emp_draft.fullname if is_draft and emp_draft.edited_fields.get('fullname') else emp.fullname,
                'eligible_for_increment': emp_draft.eligible_for_increment if is_draft and emp_draft.edited_fields.get('eligible_for_increment') else emp.eligible_for_increment,
                'company': emp.company.name,
                'department_team': emp.department_team,
                'department_group': emp_draft.department_group if is_draft and emp_draft.edited_fields.get('department_group_id') else emp.department_group,
                'section': emp_draft.section if is_draft and emp_draft.edited_fields.get('section_id') else emp.section,
                'designation': emp_draft.designation if is_draft and emp_draft.edited_fields.get('designation_id') else emp.designation,
                'location': emp_draft.location if is_draft and emp_draft.edited_fields.get('location_id') else emp.location,
                'date_of_joining': emp_draft.date_of_joining if is_draft and emp_draft.edited_fields.get('date_of_joining') else emp.date_of_joining,
                'resign': emp_draft.resign if is_draft and emp_draft.edited_fields.get('resign') else emp.resign,
                'date_of_resignation': emp_draft.date_of_resignation if is_draft and emp_draft.edited_fields.get('date_of_resignation') else emp.date_of_resignation,
                'remarks': emp_draft.remarks if is_draft and emp_draft.edited_fields.get('remarks') else emp.remarks,
                'is_draft': is_draft,
                'currentpackagedetails': None,
                'proposedpackagedetails': None,
                'financialimpactpermonth': None,
            }

            draft_data[emp.emp_id] = {'employee': {}, 'CurrentPackageDetails': {}, 'ProposedPackageDetails': {}, 'FinancialImpactPerMonth': {}}

            # ✅ Handle current package
            current_draft = getattr(emp_draft, "currentpackagedetailsdraft", None) if is_draft else None
            current_package = current_draft or getattr(emp, 'currentpackagedetails', None)
            if current_package:
                print("current_package.fuel_litre: ", current_package.fuel_litre)
                data['currentpackagedetails'] = {
                    'gross_salary': current_package.gross_salary,
                    'vehicle': current_package.vehicle,
                    'company_pickup': current_package.company_pickup,
                    'fuel_litre': current_package.fuel_litre,
                    'fuel_allowance': current_package.fuel_allowance,
                    'mobile_provided': current_package.mobile_provided,
                    'total': current_package.total,
                }

            # ✅ Handle proposed package
            proposed_draft = getattr(emp_draft, "proposedpackagedetailsdraft", None) if is_draft else None
            proposed_package = proposed_draft or getattr(emp, 'proposedpackagedetails', None)
            if proposed_package:
                data['proposedpackagedetails'] = {
                    'increment_percentage': proposed_package.increment_percentage,
                    'increased_amount': proposed_package.increased_amount,
                    'revised_salary': proposed_package.revised_salary,
                    'increased_fuel_allowance': proposed_package.increased_fuel_allowance,
                    'increased_fuel_litre': proposed_package.increased_fuel_litre,
                    'revised_fuel_allowance': proposed_package.revised_fuel_allowance,
                    'company_pickup': proposed_package.company_pickup,
                    'mobile_provided': proposed_package.mobile_provided,
                    'total': proposed_package.total,
                    'vehicle': proposed_package.vehicle,
                }

            # ✅ Handle financial impact (Prioritize draft)
            financial_draft = getattr(emp_draft, "financialimpactpermonthdraft", None) if is_draft else None
            financial_package = financial_draft or getattr(emp, 'financialimpactpermonth', None)
            if financial_package:
                data['financialimpactpermonth'] = {
                    'emp_status': financial_package.emp_status,
                    'serving_years': financial_package.serving_years,
                    'salary': financial_package.salary,
                    'gratuity': financial_package.gratuity,
                    'bonus': financial_package.bonus,
                    'leave_encashment': financial_package.leave_encashment,
                    'fuel': financial_package.fuel,
                    'vehicle': financial_package.vehicle,
                    'total': financial_package.total,
                }

            employee_data.append(data)

        return render(request, self.template_name, {
            'department': department,
            'employees': employee_data,
            'department_id': department_id,
            'company_data': company_data,
            'draft_data': draft_data,
            'fuel_rate': Configurations.objects.values_list('fuel_rate', flat=True).first(),
        })


class EmployeesView(View):
    template_name = 'employee_table_list.html'

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request):
        # department = DepartmentTeams.objects.filter(
        #     company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
        # ).first()
        department = DepartmentTeams.objects.filter(
            company=Company.objects.first()
        ).first()
        if not department:
            return render(request, 'error.html', {'error': 'Invalid department'}, status=400)

        company_data = get_companies_and_department_teams(request.user)
        employees = Employee.objects.all().select_related(
            'company', 'department_team', 'department_group', 'section', 'designation', 'location'
        ).prefetch_related(
            'currentpackagedetails', 'proposedpackagedetails', 'financialimpactpermonth', 'drafts'
        )

        employee_data = []
        draft_data = {}

        for emp in employees:
            data = {
                'emp_id': emp.emp_id,
                'fullname': emp.fullname,
                'eligible_for_increment': emp.eligible_for_increment,
                'company': emp.company.name,
                'department_team': emp.department_team,
                'department_group': emp.department_group,
                'section': emp.section,
                'designation': emp.designation,
                'location': emp.location,
                'date_of_joining': emp.date_of_joining,
                'resign': emp.resign,
                'date_of_resignation': emp.date_of_resignation,
                'currentpackagedetails': None,
                'proposedpackagedetails': None,
                'employee_status': emp.financialimpactpermonth.emp_status,
            }

            employee_data.append(data)

        return render(request, self.template_name, {
            'department': department,
            'employees': employee_data,
            'company_data': company_data,
        })


@method_decorator(login_required, name='dispatch')
@method_decorator(cache_control(no_cache=True, must_revalidate=True, no_store=True), name='dispatch')
@method_decorator(ensure_csrf_cookie, name='dispatch')
class GetEmployeeDataView(View):
    def get(self, request, employee_id):
        try:
            # Optimize queries and ensure HR authorization
            employee = Employee.objects.select_related(
                'department_group', 'section', 'designation', 'location', 'department_team__company'
            ).filter(
                emp_id=employee_id,
                department_team__company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
            ).first()

            if not employee:
                return JsonResponse({'error': 'Employee not found or not authorized'}, status=404)

            # Fetch drafts
            emp_draft = EmployeeDraft.objects.filter(employee=employee).first()
            current_draft = CurrentPackageDetailsDraft.objects.filter(employee=employee).first()
            proposed_draft = ProposedPackageDetailsDraft.objects.filter(employee=employee).first()
            financial_draft = FinancialImpactPerMonthDraft.objects.filter(employee=employee).first()

            # Decide source (draft vs live)
            use_emp = emp_draft if emp_draft else employee
            use_current = current_draft if current_draft else CurrentPackageDetails.objects.filter(employee=employee).first()
            use_proposed = proposed_draft if proposed_draft else ProposedPackageDetails.objects.filter(employee=employee).first()
            use_financial = financial_draft if financial_draft else FinancialImpactPerMonth.objects.filter(employee=employee).first()

            # Helper to format date
            def fmt_date(date):
                return date.strftime('%Y-%m-%d') if date else ''

            # Helper to safely convert decimal/float fields to strings
            def fmt_float(value):
                return str(value) if value is not None else ''

            data = {
                'employee': {
                    "emp_id" : getattr(use_emp, 'emp_id', ''),
                    'fullname': getattr(use_emp, 'fullname', ''),
                    'department_group_id': getattr(getattr(use_emp, 'department_group', None), 'id', None),
                    'section_id': getattr(getattr(use_emp, 'section', None), 'id', None),
                    'designation_id': getattr(getattr(use_emp, 'designation', None), 'id', None),
                    'location_id': getattr(getattr(use_emp, 'location', None), 'id', None),
                    'date_of_joining': fmt_date(getattr(use_emp, 'date_of_joining', None)),
                    'resign': getattr(use_emp, 'resign', False),
                    'date_of_resignation': fmt_date(getattr(use_emp, 'date_of_resignation', None)),
                    'eligible_for_increment': getattr(use_emp, 'eligible_for_increment', False),
                    'remarks': getattr(use_emp, 'remarks', '') or '',
                    'image': employee.image.url if getattr(employee, 'image', None) else ''
                },
                'current_package': {
                    'gross_salary': fmt_float(getattr(use_current, 'gross_salary', None)),
                    'company_pickup': getattr(getattr(use_current, 'company_pickup', None), 'id', ''),
                    'vehicle_id': getattr(getattr(use_current, 'vehicle', None), 'id', ''),
                    'fuel_litre': fmt_float(getattr(use_current, 'fuel_litre', None)),
                    'mobile_allowance': fmt_float(getattr(use_current, 'mobile_allowance', None)),
                },
                'proposed_package': {
                    'increment_percentage': fmt_float(getattr(use_proposed, 'increment_percentage', None)),
                    'increased_amount': fmt_float(getattr(use_proposed, 'increased_amount', None)),
                    'increased_fuel_amount': fmt_float(getattr(use_proposed, 'increased_fuel_amount', None)),
                    'mobile_allowance': fmt_float(getattr(use_proposed, 'mobile_allowance', None)),
                    'company_pickup': getattr(getattr(use_proposed, 'company_pickup', None), 'id', ''),
                    'vehicle_id': getattr(getattr(use_proposed, 'vehicle', None), 'id', ''),
                },
                'financial_impact': {
                    'emp_status_id': getattr(getattr(use_financial, 'emp_status', None), 'id', ''),
                    'serving_years': fmt_float(getattr(use_financial, 'serving_years', None)),
                    'salary': fmt_float(getattr(use_financial, 'salary', None)),
                    'gratuity': fmt_float(getattr(use_financial, 'gratuity', None)),
                }
            }

            return JsonResponse({'data': data})

        except Employee.DoesNotExist:
            return JsonResponse({'error': 'Employee not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class CreateEmployeeView(View):
    template_name = 'create_employee.html'

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = permission_required('user.add_employee', raise_exception=True)(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request):
        company_data = get_companies_and_department_teams(request.user)
        # Get the first company the user is assigned to
        company_id = hr_assigned_companies.objects.filter(hr=request.user).values_list('company', flat=True).first()
        
        if not company_id:
            raise PermissionDenied("No company assigned to this user.")

        return render(request, self.template_name, {
            'company_id': company_id,
            'company_data': company_data
        })

    def post(self, request):
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({'error': 'Invalid request'}, status=400)

        try:
            with transaction.atomic():
                step = request.POST.get('step')
                company_id = hr_assigned_companies.objects.filter(hr=request.user).values_list('company', flat=True).first()
                if not company_id:
                    return JsonResponse({'error': 'No company assigned to this user'}, status=403)

                # STEP 1: Create Employee
                if step == 'employee':
                    # Validate department_team_id
                    department_team_id = request.POST.get('department_team_id')
                    department = get_object_or_404(
                        DepartmentTeams,
                        id=department_team_id,
                        company=company_id,
                        is_deleted=False
                    )

                    # Disconnect signals
                    post_save.disconnect(update_increment_summary_employee, sender=Employee)
                    post_save.disconnect(update_increment_summary, sender=CurrentPackageDetails)
                    post_save.disconnect(update_increment_summary, sender=ProposedPackageDetails)
                    post_save.disconnect(update_increment_summary, sender=FinancialImpactPerMonth)

                    # Parse date_of_joining from POST data
                    date_str = request.POST.get('date_of_joining')
                    date_of_joining = None
                    eligible_for_increment = False

                    if date_str:
                        try:
                            # Adjust format if needed, e.g., "%Y-%m-%d"
                            date_of_joining = datetime.strptime(date_str, "%Y-%m-%d").date()
                            if date_of_joining <= (date.today() - relativedelta(months=6)):
                                eligible_for_increment = True
                        except ValueError:
                            # Handle invalid date format if necessary
                            pass

                    emp_id = request.POST.get('emp_id')

                    # Get or create employee by emp_id
                    employee, created = Employee.objects.get_or_create(emp_id=emp_id, defaults={
                        'fullname': request.POST.get('fullname'),
                        'company_id': company_id,
                        'department_team': department,
                        'department_group_id': request.POST.get('department_group_id') or None,
                        'section_id': request.POST.get('section_id') or None,
                        'designation_id': request.POST.get('designation_id') or None,
                        'location_id': request.POST.get('location_id') or None,
                        'date_of_joining': request.POST.get('date_of_joining') or None,
                        'resign': request.POST.get('resign') == 'true',
                        'date_of_resignation': request.POST.get('date_of_resignation') or None,
                        'remarks': request.POST.get('remarks') or '',
                        'image': request.FILES.get('image') if 'image' in request.FILES else None,
                        'eligible_for_increment': eligible_for_increment,
                    })

                    designation_id_str = request.POST.get('designation_id')
                    if designation_id_str:
                        designation_id = int(designation_id_str)

                        # Get the "intern" designation object (if exists)
                        intern = Designation.objects.filter(title__iexact="intern", company=employee.company).first()

                        if intern and designation_id == intern.id:
                            is_intern = True
                            promoted_from_intern_date = None
                        else:
                            is_intern = False
                            promoted_from_intern_date = date.today()

                    # If the employee already existed, update the fields
                    if not created:
                        employee.fullname = request.POST.get('fullname')
                        employee.company_id = company_id
                        employee.department_team = department
                        employee.department_group_id = request.POST.get('department_group_id') or None
                        employee.section_id = request.POST.get('section_id') or None
                        employee.designation_id = request.POST.get('designation_id') or None
                        employee.location_id = request.POST.get('location_id') or None
                        employee.date_of_joining = request.POST.get('date_of_joining') or None
                        employee.resign = request.POST.get('resign') == 'true'
                        employee.date_of_resignation = request.POST.get('date_of_resignation') or None
                        employee.remarks = request.POST.get('remarks') or ''
                        if 'image' in request.FILES:
                            employee.image = request.FILES.get('image')
                        employee.eligible_for_increment = eligible_for_increment
                        employee.is_intern = is_intern
                        employee.promoted_from_intern_date = promoted_from_intern_date
                        employee.save()
                    else:
                        employee.is_intern = is_intern
                        employee.promoted_from_intern_date = promoted_from_intern_date
                        employee.save()

                    # Create related models
                    CurrentPackageDetails.objects.get_or_create(employee=employee)
                    ProposedPackageDetails.objects.get_or_create(employee=employee)
                    FinancialImpactPerMonth.objects.get_or_create(employee=employee)

                    # Reconnect signals
                    post_save.connect(update_increment_summary_employee, sender=Employee)
                    post_save.connect(update_increment_summary, sender=CurrentPackageDetails)
                    post_save.connect(update_increment_summary, sender=ProposedPackageDetails)
                    post_save.connect(update_increment_summary, sender=FinancialImpactPerMonth)

                    # Manually trigger signal
                    update_increment_summary_employee(sender=Employee, instance=employee, created=True)

                    logger.debug(f"Employee created: {employee.emp_id}")
                    return JsonResponse({'message': 'Employee created', 'employee_id': employee.id})  # Return ID, not emp_id

                # STEP 2: Update Current Package
                elif step == 'current_package':
                    employee_id = request.POST.get('employee_id')
                    employee = get_object_or_404(Employee, id=employee_id, company_id=company_id)
                    current_package = get_object_or_404(CurrentPackageDetails, employee=employee)

                    current_package.gross_salary = request.POST.get('gross_salary') or None
                    current_package.vehicle_id = request.POST.get('vehicle_id') or None
                    current_package.mobile_provided = request.POST.get('mobile_provided') == 'true'
                    current_package.company_pickup = request.POST.get('company_pickup') == 'true'
                    current_package.fuel_litre = request.POST.get('fuel_litre') or None
                    try:
                        fuel_litre = float(request.POST.get('fuel_litre')) if request.POST.get('fuel_litre') else None
                        fuel_rate = Configurations.objects.values_list('fuel_rate', flat=True).first()
                        current_package.fuel_allowance = fuel_litre * fuel_rate if fuel_litre and fuel_rate else None
                    except (TypeError, ValueError):
                        current_package.fuel_allowance = None

                    current_package.save()
                    logger.debug(f"CurrentPackageDetails updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Current Package updated', 'employee_id': employee.id})

                # STEP 4: Update Financial Impact
                elif step == 'financial_impact':
                    employee_id = request.POST.get('employee_id')
                    employee = get_object_or_404(Employee, id=employee_id, company_id=company_id)
                    financial_impact = get_object_or_404(FinancialImpactPerMonth, employee=employee)

                    financial_impact.emp_status_id = request.POST.get('emp_status_id') or None
                    financial_impact.save()

                    logger.debug(f"FinancialImpactPerMonth updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Employee created successfully', 'employee_id': employee.id})

                return JsonResponse({'error': 'Invalid step'}, status=400)

        except Exception as e:
            logger.error(f"Error in CreateEmployeeView: {str(e)}")
            return JsonResponse({'error': 'Invalid data'}, status=400)


class EmployeeDetailView(View):
    template_name = 'employee_detail.html'

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = permission_required('user.view_employee', raise_exception=True)(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, employee_id):
        employee = get_object_or_404(Employee, emp_id=employee_id)
        company = Company.objects.all().first()
        current_package = CurrentPackageDetails.objects.filter(employee=employee).first()

        return render(request, self.template_name, {
            'employee': employee,
            'company': company,
            'current_package': current_package,
        })


class UpdateEmployeeView(View):
    template_name = 'update_employee.html'

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = permission_required('user.change_employee', raise_exception=True)(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, employee_id):
        company_data = get_companies_and_department_teams(request.user)
        company = Company.objects.all().first()
        employee = get_object_or_404(Employee, emp_id=employee_id)

        # Get related records if exist
        current_package = CurrentPackageDetails.objects.filter(employee=employee).first()
        proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first()
        financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first()

        return render(request, self.template_name, {
            'employee_id': employee_id,
            'employee': employee,
            'company': company,
            'current_package': current_package,
            'proposed_package': proposed_package,
            'financial_impact': financial_impact,
            'company_data': company_data
        })

    def post(self, request, employee_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                company_data = get_companies_and_department_teams(request.user)
                employee = get_object_or_404(Employee, emp_id=employee_id)
                step = request.POST.get('step')

                # --- Update Employee Info ---
                if step == 'employee':
                    # Parse date_of_joining from POST data
                    date_str = request.POST.get('date_of_joining')
                    date_of_joining = None
                    eligible_for_increment = False

                    if date_str:
                        try:
                            # Adjust format if needed, e.g., "%Y-%m-%d"
                            date_of_joining = datetime.strptime(date_str, "%Y-%m-%d").date()
                            if date_of_joining <= (date.today() - relativedelta(months=6)):
                                eligible_for_increment = True
                        except ValueError:
                            # Handle invalid date format if necessary
                            pass

                    employee.emp_id = request.POST.get('emp_id') or employee.emp_id
                    employee.fullname = request.POST.get('fullname') or employee.fullname
                    employee.department_team_id = request.POST.get('department_team_id') or None
                    employee.department_group_id = request.POST.get('department_group_id') or None
                    employee.section_id = request.POST.get('section_id') or None
                    employee.designation_id = request.POST.get('designation_id') or None

                    designation_id_str = request.POST.get('designation_id')
                    if designation_id_str:
                        designation_id = int(designation_id_str)

                        # Get the "intern" designation object (if exists)
                        intern = Designation.objects.filter(title__iexact="intern", company=employee.company).first()

                        if intern and designation_id == intern.id:
                            employee.is_intern = True
                            employee.promoted_from_intern_date = None
                        else:
                            if employee.is_intern == True:
                                employee.promoted_from_intern_date = date.today()
                                date_of_joining = date.today()
                            employee.is_intern = False

                    employee.location_id = request.POST.get('location_id') or None
                    employee.date_of_joining = date_of_joining
                    employee.eligible_for_increment = eligible_for_increment
                    employee.date_of_resignation = request.POST.get('date_of_resignation') or None

                    if request.POST.get('date_of_resignation'):
                        employee.resign = True
                    else:
                        employee.resign = False

                    employee.remarks = request.POST.get('remarks') or ''
                    # employee.eligible_for_increment = request.POST.get('eligible_for_increment') == 'true'
                    if 'image' in request.FILES:
                        employee.image = request.FILES['image']
                    employee.save()
                    logger.debug(f"Employee updated: {employee_id}")

                    employee_draft = EmployeeDraft.objects.filter(employee=employee)
                    if employee_draft.exists():
                        employee_draft = employee_draft.first()
                        employee_draft.emp_id = employee.emp_id
                        employee_draft.fullname = employee.fullname
                        employee_draft.department_team_id = employee.department_team_id
                        employee_draft.department_group_id = employee.department_group_id       
                        employee_draft.section_id = employee.section_id
                        employee_draft.designation_id = employee.designation_id
                        employee_draft.location_id = employee.location_id
                        employee_draft.date_of_joining = employee.date_of_joining
                        employee_draft.date_of_resignation = employee.date_of_resignation
                        employee_draft.resign = employee.resign
                        employee_draft.image = employee.image
                        employee_draft.save()

                    return JsonResponse({'message': 'Employee updated', 'employee_id': employee_id})

                # --- Update Current Package ---
                elif step == 'current_package':
                    current_package, _ = CurrentPackageDetails.objects.get_or_create(employee=employee)
                    current_package.gross_salary = request.POST.get('gross_salary') or None
                    current_package.company_pickup = request.POST.get('company_pickup_current') == 'true'
                    current_package.vehicle_id = request.POST.get('vehicle_id') or None
                    current_package.mobile_provided = request.POST.get('mobile_provided') == 'true'
                    if not request.POST.get('fuel_litre'):
                            current_package.fuel_allowance = request.POST.get('fuel_allowance') or None
                    else:
                        fuel_rate = Configurations.objects.values_list('fuel_rate', flat=True).first()
                        try:
                            fuel_litre = float(request.POST.get('fuel_litre'))
                            current_package.fuel_allowance = fuel_litre * fuel_rate
                        except (TypeError, ValueError):
                            current_package.fuel_allowance = None
                    current_package.fuel_litre = request.POST.get('fuel_litre') or None

                    current_package.fuel_litre = request.POST.get('fuel_litre') or None
                    current_package.save()
                    logger.debug(f"CurrentPackageDetails updated for employee: {employee_id}")

                    employee_draft = EmployeeDraft.objects.filter(employee=employee)
                    if employee_draft.exists():
                        current_package_details_draft = CurrentPackageDetailsDraft.objects.filter(employee_draft=employee_draft.first())
                        if current_package_details_draft.exists():
                            current_package_details_draft = current_package_details_draft.first()
                            current_package_details_draft.gross_salary = current_package.gross_salary
                            current_package_details_draft.company_pickup = current_package.company_pickup
                            current_package_details_draft.vehicle_id = current_package.vehicle_id
                            current_package_details_draft.mobile_provided = current_package.mobile_provided
                            current_package_details_draft.fuel_allowance = current_package.fuel_allowance
                            current_package_details_draft.fuel_allowance = current_package.fuel_allowance
                            current_package_details_draft.fuel_litre = current_package.fuel_litre
                            current_package_details_draft.save()

                    return JsonResponse({'message': 'Current Package updated'})

                # --- Update Financial Impact ---
                elif step == 'financial_impact':
                    financial_impact, _ = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
                    financial_impact.emp_status_id = request.POST.get('emp_status_id') or None
                    # financial_impact.serving_years = request.POST.get('serving_years') or None
                    # financial_impact.salary = request.POST.get('salary') or None
                    # financial_impact.gratuity = request.POST.get('gratuity') or None
                    financial_impact.save()

                    employee_draft = EmployeeDraft.objects.filter(employee=employee)
                    if employee_draft.exists():
                        financial_impact_draft = FinancialImpactPerMonthDraft.objects.filter(employee_draft=employee_draft.first())
                        if financial_impact_draft.exists():
                            financial_impact_draft = financial_impact_draft.first()
                            financial_impact_draft.emp_status_id = financial_impact.emp_status_id
                            financial_impact_draft.save()

                    logger.debug(f"FinancialImpactPerMonth updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Financial Impact updated'})

                return JsonResponse({'error': 'Invalid step'}, status=400)

            except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
                logger.error(f"Error in UpdateEmployeeView: {str(e)}")
                return JsonResponse({'error': 'Invalid data'}, status=400)

        return JsonResponse({'error': 'Invalid request'}, status=400)


class DeleteEmployeeView(View):

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = permission_required('user.delete_employee', raise_exception=True)(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def post(self, request, employee_id):
        """Handle employee deletion via AJAX."""
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({'error': 'Invalid request'}, status=400)

        try:
            employee = get_object_or_404(Employee, emp_id=employee_id)
            employee.is_deleted = True
            employee.save()
            
            logger.debug(f"Employee deleted: {employee_id}")
            return JsonResponse({'message': 'Employee deleted successfully'})

        except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist):
            logger.error("Error in DeleteEmployeeView: Employee or department not found")
            return JsonResponse({'error': 'Invalid data'}, status=400)


class GetFormulasView(View):
    def get(self, request):
        department_team_id = request.GET.get('department_team_id')
        print(department_team_id)
        if department_team_id:
            configurations_data = Configurations.objects.values('fuel_rate', 'bonus_constant_multiplier').first()
            formulas = FieldFormula.objects.filter(department_team_id=department_team_id).exclude(formula__target_model='IncrementDetailsSummary').select_related('formula')
            ordered = topological_sort(formulas, company=Company.objects.all().first(), employee=None, department_team=DepartmentTeams.objects.filter(id=department_team_id).first())

            # Create a custom order using Case and When
            order_conditions = [
                When(formula__target_model=model, formula__target_field=field, then=idx)
                for idx, (model, field) in enumerate(ordered)
            ]

            # Apply the custom order to the queryset
            formulas_sorted = formulas.order_by(
                Case(*order_conditions, default=len(ordered), output_field=models.IntegerField())
            )

            # Serialize the sorted queryset
            field_formulas_data = FieldFormulaSerializer(instance=formulas_sorted, many=True).data
            print("field_formulas_data:", field_formulas_data)
            return JsonResponse({'field_formulas_data': list(field_formulas_data), 'configurations_data': configurations_data})
        return JsonResponse({'field_formulas_data': []})


class GetDataView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, table, id):
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({'error': 'Invalid request'}, status=400)

        try:
            if table == 'employee':
                logger.debug(f"Fetching employee with emp_id: {id}")

                employee = Employee.objects.filter(
                    emp_id=id,
                    department_team__company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                ).first()

                if not employee:
                    logger.error(f"Employee with emp_id {id} not found or not authorized")
                    return JsonResponse({'error': f'Employee with ID {id} not found'}, status=404)

                current_package = CurrentPackageDetails.objects.filter(employee=employee).first() or {}
                proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first() or {}
                financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first() or {}

                data = {
                    'employee': {
                        "emp_id" : employee.emp_id,
                        'fullname': employee.fullname,
                        'department_team_id': employee.department_team_id,
                        'department_group_id': employee.department_group_id,
                        'section_id': employee.section_id,
                        'designation_id': employee.designation_id,
                        'location_id': employee.location_id,
                        'date_of_joining': employee.date_of_joining.isoformat() if employee.date_of_joining else '',
                        'resign': employee.resign,
                        'date_of_resignation': employee.date_of_resignation.isoformat() if employee.date_of_resignation else '',
                        'eligible_for_increment': employee.eligible_for_increment,
                        'remarks': employee.remarks or '',
                        'image': employee.image.url if employee.image else ''
                    },
                    'current_package': {
                        'gross_salary': str(current_package.gross_salary) if current_package and current_package.gross_salary else '',
                        'company_pickup': current_package.company_pickup if current_package else False,
                        'vehicle_id': current_package.vehicle_id if current_package else '',
                        'mobile_provided': current_package.mobile_provided if current_package else False,
                        'fuel_allowance': str(current_package.fuel_allowance) if current_package and current_package.fuel_allowance else '',
                        'fuel_litre': str(current_package.fuel_litre) if current_package and current_package.fuel_litre else ''
                    },
                    'proposed_package': {
                        'increment_percentage': str(proposed_package.increment_percentage) if proposed_package and proposed_package.increment_percentage else '',
                        'revised_salary': str(proposed_package.revised_salary) if proposed_package and proposed_package.revised_salary else '',
                        'mobile_provided': proposed_package.mobile_provided if proposed_package else False,
                        'company_pickup': proposed_package.company_pickup if proposed_package else False,
                        'vehicle_id': proposed_package.vehicle_id if proposed_package else '',
                        'increased_fuel_litre': str(proposed_package.increased_fuel_litre) if proposed_package and proposed_package.increased_fuel_litre else '',
                        'increased_fuel_allowance': str(proposed_package.increased_fuel_allowance) if proposed_package and proposed_package.increased_fuel_allowance else '',
                    },
                    'financial_impact': {
                        'emp_status_id': str(financial_impact.emp_status_id) if financial_impact and financial_impact.emp_status_id else '',
                        'serving_years': str(financial_impact.serving_years) if financial_impact and financial_impact.serving_years else '',
                        'salary': str(financial_impact.salary) if financial_impact and financial_impact.salary else '',
                        'gratuity': str(financial_impact.gratuity) if financial_impact and financial_impact.gratuity else ''
                    }
                }

                return JsonResponse({'data': data})

            return JsonResponse({'error': 'Invalid table'}, status=400)

        except Exception as e:
            logger.error(f"Error in GetDataView: {str(e)}")
            return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)


class DepartmentGroupsSectionsView(View):
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = DepartmentGroupsSerializer(DepartmentGroups.objects.all(), many=True).data
            return JsonResponse({'data': data})
        return JsonResponse({'error': 'Invalid request'}, status=400)


class DesignationsView(View):
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            company_id = request.GET.get('company_id')
            if not company_id:
                return JsonResponse({'error': 'company_id required'}, status=400)
            print(company_id)
            data = DesignationSerializer(Designation.objects.filter(company_id=company_id), many=True).data
            return JsonResponse({'data': data})
        return JsonResponse({'error': 'Invalid request'}, status=400)


class DesignationCreateView(View):
    def post(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = json.loads(request.body)
            serializer = DesignationCreateSerializer(data=data)
            if serializer.is_valid():
                designation = serializer.save()
                return JsonResponse({'id': designation.id, 'title': designation.title})
            return JsonResponse({'error': serializer.errors}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)
    

class LocationsView(View):
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            locations = Location.objects.all()
            if locations.exists():
                data = LocationsSerializer(locations, many=True).data
            else:
                data = []
            return JsonResponse({'data': data})
        return JsonResponse({'error': 'Invalid request'}, status=400)


class EmployeeStatusView(View):
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            employee_status = EmployeeStatus.objects.all()
            
            if employee_status.exists():
                data = EmployeeStatusSerializer(EmployeeStatus.objects.all(), many=True).data
                return JsonResponse({'data': data})
            
            return JsonResponse({'data': []})
        
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    
class VehiclesDropdownView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                vehicles = VehicleModel.objects.select_related('brand').all()
                data = [
                    {
                        'id': vehicle.id,
                        'brand_name': vehicle.brand.name,
                        'model_name': vehicle.model_name,
                        'engine_cc': vehicle.engine_cc,
                        'label': f"{vehicle.brand.name} {vehicle.model_name} ({vehicle.engine_cc})"
                    }
                    for vehicle in vehicles
                ]
                return JsonResponse({'data': data})
            except Exception as e:
                return JsonResponse({'error': f'Error fetching vehicles: {str(e)}'}, status=500)
        return JsonResponse({'error': 'Invalid request'}, status=400)


class FormulaListView(PermissionRequiredMixin, View):
    permission_required = "user.view_formula"
    template_name = "view_formula.html"

    def get(self, request):
        formulas = Formula.objects.all().order_by('-id')  # latest first
        print([formula.__dict__ for formula in formulas])
        return render(request, self.template_name, {
            'formulas': formulas,
            'company_data': get_companies_and_department_teams(request.user)
        })


class CreateFormulaView(PermissionRequiredMixin, View):
    permission_required = "user.add_formula"
    template_name = "create_formula.html"

    def get(self, request):
        form = FormulaForm()
        field_references = FieldReference.objects.all()
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references,
            'company_data': get_companies_and_department_teams(request.user)
        })

    def post(self, request):
        form = FormulaForm(request.POST)
        field_references = FieldReference.objects.all()
        if form.is_valid():
            form.save()
            messages.success(request, "Formula created successfully!")
            return redirect("view_formula")
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references,
            'company_data': get_companies_and_department_teams(request.user)
        })
    
class EditFormulaView(PermissionRequiredMixin, View):
    permission_required = "user.change_formula"
    template_name = "update_formula.html"

    def get(self, request, pk):
        formula = get_object_or_404(Formula, pk=pk)
        form = FormulaForm(instance=formula)
        field_references = FieldReference.objects.all()
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references,
            'formula': formula,
            'company_data': get_companies_and_department_teams(request.user)
        })

    def post(self, request, pk):
        formula = get_object_or_404(Formula, pk=pk)
        form = FormulaForm(request.POST, instance=formula)
        field_references = FieldReference.objects.all()
        if form.is_valid():
            form.save()
            messages.success(request, "Formula updated successfully!")
            return redirect("view_formula")
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references,
            'formula': formula,
            'company_data': get_companies_and_department_teams(request.user)
        })


# For Manage Formula CRUD
class FieldFormulaListView(PermissionRequiredMixin, View):
    permission_required = "user.view_fieldformula"
    template_name = "view_field_formulas.html"

    def get(self, request):
        company_data = get_companies_and_department_teams(request.user)
        field_formulas = FieldFormula.objects.all().order_by('company', 'department_team')
        field_references = FieldReference.objects.all()
        return render(request, self.template_name, {
            'field_formulas': field_formulas,
            'field_references': field_references,
            'company_data': company_data
        })
        

class CreateFieldFormulaView(PermissionRequiredMixin, View):
    permission_required = "user.add_fieldformula"
    template_name = "create_field_formula.html"

    def get(self, request):
        form = FieldFormulaForm(user=request.user)  # Pass user
        field_references = FieldReference.objects.all()
        company_data = get_companies_and_department_teams(request.user)
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references,
            'company_data': company_data
        })

    def post(self, request):
        # Make a mutable copy of POST data
        post_data = request.POST.copy()

        # Modify or add fields
        post_data['company'] = Company.objects.values_list('id', flat=True).first()
        # request.POST['company'] = Company.objects.values_list('id', flat=True).first()
        form = FieldFormulaForm(user=request.user, data=post_data)  # Pass user
        field_references = FieldReference.objects.all()
        company_data = get_companies_and_department_teams(request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Field Formula created successfully!")
            return redirect("view_field_formulas")
        else:
            print(form.errors)
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references,
            'company_data': company_data
        })


class EditFieldFormulaView(PermissionRequiredMixin, View):
    permission_required = "user.change_fieldformula"
    template_name = "update_field_formula.html"

    def get(self, request, pk):
        field_formula = get_object_or_404(FieldFormula, pk=pk)
        form = FieldFormulaForm(user=request.user, instance=field_formula)
        field_references = FieldReference.objects.all()
        company_data = get_companies_and_department_teams(request.user)
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references,
            'company_data': company_data,
            'field_formula': field_formula
        })

    def post(self, request, pk):
        # Make a mutable copy of POST data
        post_data = request.POST.copy()

        print("pk: ", pk)

        # Modify or add fields
        post_data['company'] = Company.objects.values_list('id', flat=True).first()

        field_formula = get_object_or_404(FieldFormula, pk=pk)
        form = FieldFormulaForm(post_data, instance=field_formula ,  user=request.user)
        field_references = FieldReference.objects.all()
        company_data = get_companies_and_department_teams(request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Field Formula updated successfully!")
            return redirect("view_field_formulas")
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references,
            'company_data': company_data,
            'field_formula': field_formula
        })



class GetModelFieldsView(View):
    def get(self, request):
        model_name = request.GET.get("model_name")
        if not model_name:
            return JsonResponse({"fields": []})
        try:
            model = apps.get_model('user', model_name)
        except LookupError:
            return JsonResponse({"fields": []})
        fields = [f.name for f in model._meta.get_fields() if not f.is_relation]
        return JsonResponse({"fields": fields})



class GetCompanyDepartmentsEmployeesView(View):
    def get(self, request):
        company_id = request.GET.get('company_id')
        if company_id:
            department_teams = DepartmentTeams.objects.filter(company_id=company_id).values('id', 'name')
            employees = Employee.objects.filter(company_id=company_id).values('emp_id', name=models.F('fullname'))
            return JsonResponse({
                'department_teams': list(department_teams),
                'employees': list(employees)
            })
        return JsonResponse({'department_teams': [], 'employees': []})


class GetDepartmentEmployeesView(View):
    def get(self, request):
        company_id = request.GET.get('company_id')
        department_team_id = request.GET.get('department_team_id')
        if company_id and department_team_id:
            employees = Employee.objects.filter(
                company_id=company_id,
                department_team_id=department_team_id
            ).values('emp_id', name=models.F('fullname'))
            return JsonResponse({'employees': list(employees)})
        return JsonResponse({'employees': []})


'''
Updated save draft view
'''

class SaveDraftView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def post(self, request, department_id):
        try:
            data = json.loads(request.body)
            print("data: ", data)
            drafts_saved = False
            # with transaction.atomic():
            return_saved_message = False
            for employee_id, tabs in data.items():
                print("tabs: ", tabs)
                employee = Employee.objects.filter(emp_id=employee_id, department_team_id=department_id).first()
                print("employee: ", employee)
                if not employee:
                    logger.error(f"Employee {employee_id} not found for department {department_id}")
                    return JsonResponse({'error': f'Employee {employee_id} not found'}, status=404)

                has_changes = False
                employee_draft_edited = {}
                current_package_edited = {}
                proposed_package_edited = {}
                financial_impact_edited = {}

                # Detect changes
                for tab, fields in tabs.items():
                    print("tab, fields: ", tab, fields)
                    if tab == 'employee':
                        for field, value in fields.items():
                            print("field, value: ", field, value)
                            current_value = getattr(employee, field, None)
                            print("current_value: ", current_value)
                            if field.endswith('_id'):
                                current_value = getattr(getattr(employee, field.replace('_id', ''), None), 'id', None)
                                print("current_value _id: ", current_value)
                            elif isinstance(current_value, bool):
                                current_value = str(current_value).lower()
                            # if str(value) != str(current_value):
                            #     has_changes = True
                            #     employee_draft_edited[field] = True
                            #     print("employee_draft_edited: ", employee_draft_edited)
                            has_changes = True
                            employee_draft_edited[field] = True

                    elif tab == 'CurrentPackageDetails':
                        current_package = CurrentPackageDetails.objects.filter(employee=employee).first()
                        print("current_package: ", current_package)
                        for field, value in fields.items():
                            print("field, value: ", field, value)
                            current_value = getattr(current_package, field, None) if current_package else None
                            print("current_value: ", current_value)
                            if field.endswith('_id'):
                                current_value = current_value.id if current_value else None
                                print("current_value _id: ", current_value)
                            # if str(value) != str(current_value):
                            #     has_changes = True
                            #     current_package_edited[field] = True
                            has_changes = True
                            current_package_edited[field] = True

                    elif tab == 'ProposedPackageDetails':
                        proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first()
                        print("proposed_package: ", proposed_package)
                        for field, value in fields.items():
                            print("field, value: ", field, value)
                            current_value = getattr(proposed_package, field, None) if proposed_package else None
                            print("current_value: ", current_value)
                            if field.endswith('_id'):
                                current_value = current_value.id if current_value else None
                                print("current_value _id: ", current_value)
                            # if str(value) != str(current_value):
                            #     has_changes = True
                            #     proposed_package_edited[field] = True
                            has_changes = True
                            proposed_package_edited[field] = True

                    elif tab == 'FinancialImpactPerMonth':
                        financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first()
                        print("financial_impact: ", financial_impact)
                        for field, value in fields.items():
                            print("field, value: ", field, value)
                            current_value = getattr(financial_impact, field, None) if financial_impact else None
                            print("current_value: ", current_value)
                            if field.endswith('_id'):
                                current_value = current_value.id if current_value else None
                                print("current_value _id: ", current_value)
                            if str(value) != str(current_value):
                                has_changes = True
                                financial_impact_edited[field] = True

                if not has_changes:
                    print("HERE")
                    continue

                # Create or update EmployeeDraft
                employee_draft = EmployeeDraft.objects.filter(employee=employee).first()
                print("employee_draft: ", employee_draft)

                empl = tabs.get('employee', {})
                date_of_joining = employee.date_of_joining
                if empl.get('designation_id'):
                    designation_id = int(empl.get('designation_id'))

                    # Get the "intern" designation object (if exists)
                    intern = Designation.objects.filter(title__iexact="intern", company=employee.company).first()

                    if intern and designation_id == intern.id:
                        is_intern = True
                        promoted_from_intern_date = None
                    else:
                        if employee_draft and employee_draft.is_intern == True:
                            promoted_from_intern_date = date.today()
                            date_of_joining = date.today()
                        else:
                            promoted_from_intern_date = None
                        is_intern = False
                else:
                    if employee_draft:
                        is_intern = employee_draft.is_intern
                        promoted_from_intern_date = employee_draft.promoted_from_intern_date
                    else:
                        is_intern = employee.is_intern
                        promoted_from_intern_date = employee.promoted_from_intern_date

                if not employee_draft:
                    # fipm = tabs.get('financial_impact', {})
                    # if fipm.get('eligible_for_increment'):
                    #     eligible_for_increment = bool(empl.get('eligible_for_increment'))
                    # else:
                    #     eligible_for_increment = employee.eligible_for_increment

                    employee_draft = EmployeeDraft(emp_id=employee_id, resign=employee.resign, eligible_for_increment=employee.eligible_for_increment, auto_mark_eligibility=employee.auto_mark_eligibility, is_intern=is_intern, 
                        promoted_from_intern_date=promoted_from_intern_date, fullname=employee.fullname, remarks=employee.remarks, date_of_joining=employee.date_of_joining, employee=employee, company=employee.company, 
                        department_team=employee.department_team, department_group=employee.department_group, section=employee.section, designation=employee.designation, location=employee.location)
                    print("NEW employee_draft: ", employee_draft)
                    employee_draft.save()   # <-- save immediately

                # Save employee fields
                for field, value in tabs.get('employee', {}).items():
                    print("field, value: ", field, value)
                    if employee_draft_edited.get(field):
                        if field.endswith('_id'):
                            setattr(employee_draft, field, int(value) if value else None)
                        elif isinstance(getattr(EmployeeDraft, field).field, models.BooleanField):
                            setattr(employee_draft, field, value == 'true')
                        else:
                            setattr(employee_draft, field, value or None)
                            
                setattr(employee_draft, 'promoted_from_intern_date', promoted_from_intern_date if promoted_from_intern_date else None)
                setattr(employee_draft, 'is_intern', int(is_intern) if is_intern else None)
                # employee_draft.edited_fields = employee_draft_edited
                if employee_draft_edited:
                    print("employee_draft_edited: ", employee_draft_edited)

                    # empl = tabs.get('employee', {})
                    # if empl.get('eligible_for_increment'):
                    #     eligible_for_increment = bool(empl.get('eligible_for_increment'))
                    # else:
                    #     eligible_for_increment = employee.eligible_for_increment

                    existing_edited_fields = employee_draft.edited_fields
                    
                    if len(existing_edited_fields) > 0 and not isinstance(existing_edited_fields, dict):
                        existing_edited_fields = json.loads(existing_edited_fields)
                        
                    if existing_edited_fields:
                        keys_only_in_existing_edited_fields = existing_edited_fields.keys() - employee_draft_edited.keys()
                        for existing_key in keys_only_in_existing_edited_fields:
                            employee_draft_edited[existing_key]= True
                    employee_draft.edited_fields = employee_draft_edited
                    employee_draft.save()
                    drafts_saved = True

                # Save current package fields
                if current_package_edited:
                    print("if current_package_edited")
                    draft, _ = CurrentPackageDetailsDraft.objects.get_or_create(employee_draft=employee_draft)
                    for field, value in tabs.get('CurrentPackageDetails', {}).items():
                        if current_package_edited.get(field):
                            if field.endswith('_id'):
                                setattr(draft, field, int(value) if value else None)
                            elif isinstance(getattr(CurrentPackageDetailsDraft, field).field, models.BooleanField):
                                setattr(draft, field, value == 'true')
                            else:
                                setattr(draft, field, Decimal(value) if value else Decimal('0'))
                    draft.edited_fields = current_package_edited
                    draft.save()
                    drafts_saved = True

                # Save proposed package fields
                if proposed_package_edited:
                    print("if proposed_package_edited: ", proposed_package_edited)
                    proposed_package_details = employee_draft.employee.proposedpackagedetails
                    print("proposed_package_details: ", proposed_package_details)
                    draft, _ = ProposedPackageDetailsDraft.objects.get_or_create(employee_draft=employee_draft)
                    # if _:
                    #     draft.increment_percentage = proposed_package_details.increment_percentage
                    #     draft.increased_fuel_amount = proposed_package_details.increased_fuel_amount
                    #     draft.vehicle = proposed_package_details.vehicle
                    #     draft.mobile_provided = proposed_package_details.mobile_provided
                    #     draft.fuel_litre = proposed_package_details.fuel_litre
                    #     draft.vehicle_allowance = proposed_package_details.vehicle_allowance
                    #     draft.company_pickup = proposed_package_details.company_pickup
                    #     draft.is_deleted = proposed_package_details.is_deleted

                    proposed_package = tabs.get('ProposedPackageDetails', {})
                    fuel_litre = float(proposed_package.get('increased_fuel_litre', 0))
                    if fuel_litre > 0 and 'increased_fuel_allowance' in proposed_package:
                        print("Removing increased_fuel_allowance because fuel_litre > 0")
                        del proposed_package['increased_fuel_allowance']
                            
                    print("draft: ", draft)
                    for field, value in tabs.get('ProposedPackageDetails', {}).items():
                        print("field, value: ", field, value, type(value))
                        if proposed_package_edited.get(field):
                            if field == 'increased_fuel_litre':
                                setattr(draft, field, Decimal(value) if value else Decimal('0'))
                                fuel_litre = float(value)
                                if fuel_litre == 0:
                                    continue  # ❌ Skip processing if litres are zero
                                fuel_rate = Configurations.objects.values_list('fuel_rate', flat=True).first()
                                setattr(draft, 'increased_fuel_allowance', Decimal(fuel_litre * fuel_rate) if value else Decimal('0'))

                            elif field.endswith('_id'):
                                setattr(draft, field, int(value) if value else None)
                            elif isinstance(getattr(ProposedPackageDetailsDraft, field).field, models.BooleanField):
                                print("boolean field")
                                setattr(draft, field, value == True if isinstance(value, bool) else str(value).lower() == 'true')
                            else:
                                print("setting decimal")
                                setattr(draft, field, Decimal(value) if value else Decimal('0'))
                    
                    existing_edited_fields = draft.edited_fields
                    if len(existing_edited_fields) > 0 and not isinstance(existing_edited_fields, dict):
                        existing_edited_fields = json.loads(existing_edited_fields)
                    print("existing_edited_fields: ", existing_edited_fields)
                    if existing_edited_fields:
                        keys_only_in_existing_edited_fields = existing_edited_fields.keys() - proposed_package_edited.keys()
                        print("keys_only_in_existing_edited_fields: ", keys_only_in_existing_edited_fields)
                        for existing_key in keys_only_in_existing_edited_fields:
                            proposed_package_edited[existing_key]= True

                    draft.edited_fields = proposed_package_edited
                    print("saving")
                    draft.save()
                    print("saved")
                    drafts_saved = True

                # Save financial impact fields
                if financial_impact_edited:
                    print("if financial_impact_edited")
                    draft, _ = FinancialImpactPerMonthDraft.objects.get_or_create(employee_draft=employee_draft)
                    for field, value in tabs.get('FinancialImpactPerMonth', {}).items():
                        if financial_impact_edited.get(field):
                            if field.endswith('_id'):
                                setattr(draft, field, int(value) if value else None)
                            else:
                                setattr(draft, field, Decimal(value) if value else Decimal('0'))
                    draft.edited_fields = financial_impact_edited
                    draft.save()
                    drafts_saved = True

                return_saved_message = True
            
            if return_saved_message:
                return JsonResponse({'message': 'Draft saved' if drafts_saved else 'No changes to save'}, status=200)
                
            return JsonResponse({'message': 'Draft processed, No changes detected to be drafted', 'drafts_saved': drafts_saved})
        except Exception as e:
            logger.error(f"Error in SaveDraftView for department {department_id}: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)


'''
updated code for save final
'''

class SaveFinalView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    # @method_decorator(require_POST)
    def post(self, request, department_id):
        try:
            data = json.loads(request.body)
            logger.info(f"Received payload for save-final: {data}")
            updated_employees = []

            with transaction.atomic():
                for employee_id, tabs in data.items():
                    employee = Employee.objects.filter(emp_id=employee_id, department_team_id=department_id).first()
                    if not employee:
                        logger.error(f"Employee {employee_id} not found for department {department_id}")
                        return JsonResponse({'error': f'Employee {employee_id} not found'}, status=404)

                    # Employee Tab
                    if "employee" in tabs:
                        emp_data = tabs["employee"]
                        print("emp_data: ", emp_data)
                        logger.info(f"Updating employee {employee_id}: {emp_data}")
                        emp_draft = EmployeeDraft.objects.filter(employee=employee).first()
                        if emp_draft:
                            employee_edited_fields = emp_draft.edited_fields
                        
                            for field, value in employee_edited_fields.items():
                                # if field in [
                                #     'fullname', 'department_group_id', 'section_id',
                                #     'designation_id', 'location_id', 'date_of_joining',
                                #     'resign', 'date_of_resignation', 'eligible_for_increment', 'remarks'
                                # ]:
                                new_value = getattr(emp_draft, field)
                                if field in ['department_group_id', 'section_id', 'designation_id', 'location_id']:
                                    setattr(employee, field, int(new_value) if new_value else None)
                                elif field in ['resign', 'eligible_for_increment']:
                                    setattr(employee, field, new_value == True if isinstance(value, bool) else new_value == 'True')
                                elif field in ['date_of_joining', 'date_of_resignation', 'fullname', 'remarks']:
                                    setattr(employee, field, new_value or None)
                            employee.save()

                    # Current Package Tab
                    if "current_package" in tabs:
                        pkg_data = tabs["current_package"]
                        logger.info(f"Updating current_package {employee_id}: {pkg_data}")
                        current_pkg, _ = CurrentPackageDetails.objects.get_or_create(employee=employee)
                        for field, value in pkg_data.items():
                            if field in ['gross_salary', 'vehicle_id', 'fuel_allowance', 'fuel_litre', 'mobile_provided']:
                                if field == 'vehicle_id':
                                    current_pkg.vehicle_id = int(value) if value else None
                                elif field == 'mobile_provided':
                                    current_pkg.mobile_provided = value == 'true'
                                else:
                                    setattr(current_pkg, field, Decimal(value) if value else Decimal('0'))
                        current_pkg.save()

                    # Proposed Package Tab
                    if "proposed_package" in tabs:
                        prop_data = tabs["proposed_package"]
                        logger.info(f"Updating proposed_package {employee_id}: {prop_data}")
                        proposed_pkg, _ = ProposedPackageDetails.objects.get_or_create(employee=employee)

                        emp_draft = EmployeeDraft.objects.filter(employee=employee).first()
                        proposed_package_draft = ProposedPackageDetailsDraft.objects.filter(employee_draft=emp_draft).first()
                        if proposed_package_draft:
                            proposed_package_edited_fields = proposed_package_draft.edited_fields
                            for field, value in proposed_package_edited_fields.items():
                                # if field in [
                                #     'increment_percentage', 'increased_fuel_amount', 'fuel_litre',
                                #     'vehicle_allowance', 'mobile_provided'
                                # ]:
                                new_value = getattr(proposed_package_draft, field)
                                if field == 'vehicle_id':  # Adjust if vehicle_id is used
                                    proposed_pkg.vehicle_id = int(new_value) if new_value else None
                                elif field in ['mobile_provided']:
                                    setattr(proposed_pkg, field, new_value == True if isinstance(value, bool) else new_value == 'True')
                                else:
                                    setattr(proposed_pkg, field, Decimal(new_value) if new_value else Decimal('0'))
                            proposed_pkg.save()

                    # Financial Impact Tab
                    if "financial_impact" in tabs:
                        fin_data = tabs["financial_impact"]
                        logger.info(f"Updating financial_impact {employee_id}: {fin_data}")
                        financial_impact, _ = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
                        for field, value in fin_data.items():
                            if field in ['emp_status_id', 'serving_years', 'salary', 'gratuity']:
                                if field == 'emp_status_id':
                                    financial_impact.emp_status_id = int(value) if value else None
                                elif field == 'serving_years':
                                    financial_impact.serving_years = Decimal(value) if value else Decimal('0')
                                else:
                                    setattr(financial_impact, field, Decimal(value) if value else Decimal('0'))
                        financial_impact.save()

                    updated_employees.append(employee_id)

                    # Delete all related drafts
                    EmployeeDraft.objects.filter(employee=employee).delete()
                    CurrentPackageDetailsDraft.objects.filter(employee_draft__employee=employee).delete()
                    ProposedPackageDetailsDraft.objects.filter(employee_draft__employee=employee).delete()
                    FinancialImpactPerMonthDraft.objects.filter(employee_draft__employee=employee).delete()
                    logger.info(f"Deleted drafts for {employee_id}")

                if updated_employees:
                    return JsonResponse({'message': 'Changes saved successfully'}, status=200)
                else:
                    return JsonResponse({'message': 'No changes to save'}, status=200)

        except Exception as e:
            logger.error(f"Error in SaveFinalView for department {department_id}: {str(e)}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)








# class SaveFinalView(View):
#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def post(self, request, department_id):
#         try:
#             data = json.loads(request.body)
#             updated_employees = []
#             with transaction.atomic():
#                 for employee_id, tabs in data.items():
#                     employee = Employee.objects.filter(
#                         emp_id=employee_id, department_team_id=department_id
#                     ).first()
#                     if not employee:
#                         return JsonResponse({'error': f'Employee {employee_id} not found'}, status=404)

#                     employee_draft = EmployeeDraft.objects.filter(employee=employee).first()
#                     if employee_draft and employee_draft.edited_fields:  # Only process if draft has edits
#                         for tab, fields in tabs.items():

#                             # Employee Tab
#                             if tab == 'employee':
#                                 for field, value in fields.items():
#                                     if field in [
#                                         'fullname', 'department_group_id', 'section_id',
#                                         'designation_id', 'location_id', 'date_of_joining',
#                                         'resign', 'date_of_resignation', 'remarks'
#                                     ]:
#                                         if field == 'department_group_id':
#                                             employee.department_group_id = int(value) if value else None
#                                         elif field == 'section_id':
#                                             employee.section_id = int(value) if value else None
#                                         elif field == 'designation_id':
#                                             employee.designation_id = int(value) if value else None
#                                         elif field == 'location_id':
#                                             employee.location_id = int(value) if value else None
#                                         elif field == 'resign':
#                                             employee.resign = value == 'true'
#                                         elif field in ['date_of_joining', 'date_of_resignation']:
#                                             setattr(employee, field, value or None)
#                                         elif field in ['fullname', 'remarks']:
#                                             setattr(employee, field, value or None)
#                                 employee.save()

#                             # Current Package Tab
#                             elif tab == 'current_package':
#                                 current_package, created = CurrentPackageDetails.objects.get_or_create(employee=employee)
#                                 for field, value in fields.items():
#                                     if field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'mobile_allowance']:
#                                         if field == 'vehicle_id':
#                                             current_package.vehicle_id = int(value) if value else None
#                                         else:
#                                             setattr(current_package, field, Decimal(value) if value else Decimal('0'))
#                                 current_package.save()

#                             # Proposed Package Tab
#                             elif tab == 'proposed_package':
#                                 proposed_package, created = ProposedPackageDetails.objects.get_or_create(employee=employee)
#                                 for field, value in fields.items():
#                                     if field in ['increment_percentage', 'increased_fuel_amount',
#                                                  'mobile_allowance_proposed', 'vehicle_proposed_id']:
#                                         if field == 'vehicle_proposed_id':
#                                             proposed_package.vehicle_id = int(value) if value else None
#                                         elif field == 'mobile_allowance_proposed':
#                                             proposed_package.mobile_allowance = Decimal(value) if value else Decimal('0')
#                                         else:
#                                             setattr(proposed_package, field, Decimal(value) if value else Decimal('0'))
#                                 proposed_package.save()

#                             # Financial Impact Tab
#                             elif tab == 'financial_impact':
#                                 financial_impact, created = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
#                                 for field, value in fields.items():
#                                     if field == 'emp_status_id':
#                                         financial_impact.emp_status_id = int(value) if value else None
#                                     elif field in ['serving_years']:
#                                         financial_impact.serving_years = int(value) if value else None
#                                     elif field in ['salary', 'gratuity']:
#                                         setattr(financial_impact, field, Decimal(value) if value else Decimal('0'))
#                                 financial_impact.save()

#                         updated_employees.append(employee_id)
#                         employee_draft.delete()

#                 if updated_employees:
#                     EmployeeDraft.objects.filter(employee__department_team_id=department_id).delete()
#                     return JsonResponse({'message': 'Changes saved'})
#                 else:
#                     return JsonResponse({'message': 'No changes to save'}, status=200)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)


class ManageConfigurationsView(PermissionRequiredMixin, View):
    permission_required = ('user.add_configurations', 'user.change_configurations')
    template_name = 'manage_configurations.html'

    def get(self, request):
        company_data = get_companies_and_department_teams(request.user)
        config = Configurations.objects.filter(is_deleted=False).first()
        if config:
            # If a configuration exists, show edit form
            form = ConfigurationsForm(instance=config)
            return render(request, self.template_name, {'form': form, 'config': config, 'company_data': company_data})
        else:
            # If no configuration exists, show add form
            form = ConfigurationsForm()
            return render(request, self.template_name, {'form': form, 'config': None, 'company_data': company_data})

    def post(self, request):
        company_data = get_companies_and_department_teams(request.user)
        config = Configurations.objects.filter(is_deleted=False).first()
        if config:
            # If a configuration exists, update it
            if not request.user.has_perm('user.change_configurations'):
                messages.error(request, 'You do not have permission to edit configurations.')
                return redirect('manage_configurations')
            form = ConfigurationsForm(request.POST, instance=config)
        else:
            # If no configuration exists, create a new one
            if not request.user.has_perm('user.add_configurations'):
                messages.error(request, 'You do not have permission to add configurations.')
                return redirect('manage_configurations')
            form = ConfigurationsForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, f"Configuration {'updated' if config else 'added'} successfully!")
            return redirect('manage_configurations')
        return render(request, self.template_name, {'form': form, 'config': config, 'company_data': company_data})
