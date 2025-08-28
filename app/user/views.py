from .models import (
    CustomUser,
    Company,
    Section,
    VehicleModel,
    VehicleBrand,
    hr_assigned_companies,
    DepartmentTeams,
    IncrementDetailsSummary,
    Employee,
    CurrentPackageDetails,
    ProposedPackageDetails,
    FinancialImpactPerMonth,
    DepartmentGroups,
    Designation,
    Location,
    EmployeeStatus,
    Formula
)

from django.contrib.auth.mixins import PermissionRequiredMixin

from django.views import View
from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import (
    CompanyForm , 
    CustomUserForm,
    CustomUserUpdateForm,
    SectionForm,
    DepartmentGroupsForm,
    HrAssignedCompaniesForm,
    VehicleModelForm

)
from venv import logger
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import View
from django.core.exceptions import PermissionDenied
from django.db import transaction
from .models import FieldFormula, FieldReference
from .forms import FieldFormulaForm, FormulaForm, VehicleBrandForm
from django.apps import apps
from django.db import models

from permissions import PermissionRequiredMixin

from .utils import get_companies_and_department_teams
from .serializer import (
    IncrementDetailsSummarySerializer,
    DepartmentGroupsSerializer,
    DesignationSerializer,
    DesignationCreateSerializer,
    LocationsSerializer,
    EmployeeStatusSerializer

)

import json


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
            user = form.save()
            user.is_staff = True
            user.is_superuser = False
            user.save()
            messages.success(request, "User added successfully!")
            return redirect("view_users")
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
        sections = Section.objects.filter(is_deleted=False)
        return render(request, self.template_name, {"sections": sections})


# --- ADD SECTION ---
class AddSectionView(PermissionRequiredMixin, View):
    permission_required = "user.add_section"
    template_name = "add_section.html"

    def get(self, request):
        form = SectionForm()
        return render(request, self.template_name, {"form": form})

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
        section = get_object_or_404(Section, pk=pk, is_deleted=False)
        form = SectionForm(instance=section)
        return render(request, self.template_name, {"form": form, "section": section})

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
        groups = DepartmentGroups.objects.filter(is_deleted=False)
        return render(request, self.template_name, {"groups": groups})


# --- ADD DEPARTMENT GROUP ---
class AddDepartmentGroupView(PermissionRequiredMixin, View):
    permission_required = "user.add_departmentgroups"
    template_name = "add_departmentgroups.html"

    def get(self, request):
        form = DepartmentGroupsForm()
        return render(request, self.template_name, {"form": form})

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
        group = get_object_or_404(DepartmentGroups, pk=pk, is_deleted=False)
        form = DepartmentGroupsForm(instance=group)
        return render(request, self.template_name, {"form": form, "group": group})

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

        # Handle AJAX request for employee data
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            
            company_id = request.GET.get('company_id')
            if not company_id:
                return JsonResponse({'error': 'No company ID provided'}, status=400)
            try:
                increment_details_summary = IncrementDetailsSummary.objects.filter(company__id=company_id)
                print(increment_details_summary)
                if increment_details_summary.exists():
                    data = IncrementDetailsSummarySerializer(increment_details_summary, many=True).data
                else:
                    # create a dict with all serializer fields set to None
                    # fields = IncrementDetailsSummarySerializer().get_fields().keys()
                    data = []

                return JsonResponse({'data': data})
            except DepartmentTeams.DoesNotExist:
                return JsonResponse({'data': []})

        # logger.info(f"User {request.user.username} accessed HR dashboard with {len(company_data)} companies")
        return render(request, 'hr_dashboard.html', {'company_data': company_data})

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
                data = json.loads(request.body)
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
                return JsonResponse({'error': 'Invalid department or data'}, status=400)
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
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, department_id):
        # Fetch department with permission check
        department = DepartmentTeams.objects.filter(
            id=department_id,
            company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
        ).first()
        if not department:
            return render(request, 'error.html', {'error': 'Invalid department'}, status=400)

        # Get company data
        company_data = get_companies_and_department_teams(request.user)

        # Fetch employees with related data
        employees = Employee.objects.filter(department_team=department).select_related(
            'company', 'department_team', 'department_group', 'section', 'designation', 'location'
        ).prefetch_related('currentpackagedetails', 'proposedpackagedetails', 'financialimpactpermonth', 'drafts')

        employee_data = []
        draft_data = {}
        for emp in employees:
            print(emp.drafts.first())
            emp_draft = emp.drafts.first()
            is_draft = bool(emp_draft)
            print(is_draft)
            data = {
                'emp_id': emp.emp_id,
                'fullname': emp_draft.fullname if is_draft and emp_draft.edited_fields.get('fullname') else emp.fullname,
                'company': emp.company,
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
            
            draft_data[emp.emp_id] = {'employee': {}, 'current_package': {}, 'proposed_package': {}, 'financial_impact': {}}
            if is_draft:
                for field in ['fullname', 'department_group_id', 'section_id', 'designation_id', 'location_id', 'date_of_joining', 'resign', 'date_of_resignation', 'remarks']:
                    if emp_draft.edited_fields.get(field):
                        draft_data[emp.emp_id]['employee'][field] = True
            
            # Current Package
            current_draft = emp_draft.current_package_drafts.first() if is_draft else None
            current_package = emp.currentpackagedetails or current_draft
            if current_package:
                data['currentpackagedetails'] = {
                    'gross_salary': current_draft.gross_salary if is_draft and current_draft and current_draft.edited_fields.get('gross_salary') else current_package.gross_salary,
                    'vehicle': current_draft.vehicle if is_draft and current_draft and current_draft.edited_fields.get('vehicle_id') else current_package.vehicle,
                    'fuel_limit': current_draft.fuel_limit if is_draft and current_draft and current_draft.edited_fields.get('fuel_limit') else current_package.fuel_limit,
                    'mobile_allowance': current_draft.mobile_allowance if is_draft and current_draft and current_draft.edited_fields.get('mobile_allowance') else current_package.mobile_allowance,
                }
                if is_draft and current_draft:
                    for field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'mobile_allowance']:
                        if current_draft.edited_fields.get(field):
                            draft_data[emp.emp_id]['current_package'][field] = True
            
            # Proposed Package
            proposed_draft = emp_draft.proposed_package_drafts.first() if is_draft else None
            proposed_package = emp.proposedpackagedetails or proposed_draft
            if proposed_package:
                data['proposedpackagedetails'] = {
                    'increment_percentage': proposed_draft.increment_percentage if is_draft and proposed_draft and proposed_draft.edited_fields.get('increment_percentage') else proposed_package.increment_percentage,
                    'increased_amount': proposed_package.increased_amount,
                    'revised_salary': proposed_package.revised_salary,
                    'increased_fuel_amount': proposed_draft.increased_fuel_amount if is_draft and proposed_draft and proposed_draft.edited_fields.get('increased_fuel_amount') else proposed_package.increased_fuel_amount,
                    'revised_fuel_allowance': proposed_package.revised_fuel_allowance,
                    'mobile_allowance': proposed_draft.mobile_allowance if is_draft and proposed_draft and proposed_draft.edited_fields.get('mobile_allowance') else proposed_package.mobile_allowance,
                    'vehicle': proposed_draft.vehicle if is_draft and proposed_draft and proposed_draft.edited_fields.get('vehicle_id') else proposed_package.vehicle,
                }
                if is_draft and proposed_draft:
                    for field in ['increment_percentage', 'increased_fuel_amount', 'mobile_allowance', 'vehicle_id']:
                        if proposed_draft.edited_fields.get(field):
                            draft_data[emp.emp_id]['proposed_package'][field] = True
            
            # Financial Impact
            financial_draft = emp_draft.financial_impact_drafts.first() if is_draft else None
            financial_package = emp.financialimpactpermonth or financial_draft
            if financial_package:
                data['financialimpactpermonth'] = {
                    'emp_status': financial_draft.emp_status if is_draft and financial_draft and financial_draft.edited_fields.get('emp_status_id') else financial_package.emp_status,
                    'serving_years': financial_package.serving_years,
                    'salary': financial_package.salary,
                    'gratuity': financial_package.gratuity,
                    'bonus': financial_package.bonus,
                    'leave_encashment': financial_package.leave_encashment,
                    'mobile_allowance': financial_package.mobile_allowance,
                    'fuel': financial_package.fuel,
                    'total': financial_package.total,
                }
                if is_draft and financial_draft:
                    if financial_draft.edited_fields.get('emp_status_id'):
                        draft_data[emp.emp_id]['financial_impact']['emp_status_id'] = True
            
            employee_data.append(data)
        
        return render(request, 'department_table.html', {
            'department': department,
            'employees': employee_data,
            'department_id': department_id,
            'company_data': company_data,
            'draft_data': draft_data
        })


class GetEmployeeDataView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, employee_id):
        try:
            employee = Employee.objects.get(emp_id=employee_id)
            current_package = CurrentPackageDetails.objects.filter(employee=employee).first()
            proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first()
            financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first()

            return JsonResponse({
                'data': {
                    'employee': {
                        'fullname': employee.fullname,
                        'department_group_id': employee.department_group.id if employee.department_group else None,
                        'section_id': employee.section.id if employee.section else None,
                        'designation_id': employee.designation.id if employee.designation else None,
                        'location_id': employee.location.id if employee.location else None,
                        'date_of_joining': employee.date_of_joining.strftime('%Y-%m-%d') if employee.date_of_joining else '',
                        'resign': employee.resign,
                        'date_of_resignation': employee.date_of_resignation.strftime('%Y-%m-%d') if employee.date_of_resignation else '',
                        'remarks': employee.remarks or ''
                    },
                    'current_package': {
                        'gross_salary': float(current_package.gross_salary) if current_package and current_package.gross_salary else '',
                        'vehicle_id': current_package.vehicle.id if current_package and current_package.vehicle else '',
                        'fuel_limit': float(current_package.fuel_limit) if current_package and current_package.fuel_limit else '',
                        'mobile_allowance': float(current_package.mobile_allowance) if current_package and current_package.mobile_allowance else ''
                    },
                    'proposed_package': {
                        'increment_percentage': float(proposed_package.increment_percentage) if proposed_package and proposed_package.increment_percentage else '',
                        'increased_amount': float(proposed_package.increased_amount) if proposed_package and proposed_package.increased_amount else '',
                        'revised_salary': float(proposed_package.revised_salary) if proposed_package and proposed_package.revised_salary else '',
                        'increased_fuel_amount': float(proposed_package.increased_fuel_amount) if proposed_package and proposed_package.increased_fuel_amount else '',
                        'revised_fuel_allowance': float(proposed_package.revised_fuel_allowance) if proposed_package and proposed_package.revised_fuel_allowance else '',
                        'mobile_allowance': float(proposed_package.mobile_allowance) if proposed_package and proposed_package.mobile_allowance else '',
                        'vehicle_id': proposed_package.vehicle.id if proposed_package and proposed_package.vehicle else ''
                    },
                    'financial_impact': {
                        'emp_status_id': financial_impact.emp_status.id if financial_impact and financial_impact.emp_status else '',
                        'serving_years': financial_impact.serving_years if financial_impact else '',
                        'salary': float(financial_impact.salary) if financial_impact and financial_impact.salary else '',
                        'gratuity': float(financial_impact.gratuity) if financial_impact and financial_impact.gratuity else '',
                        'bonus': float(financial_impact.bonus) if financial_impact and financial_impact.bonus else '',
                        'leave_encashment': float(financial_impact.leave_encashment) if financial_impact and financial_impact.leave_encashment else '',
                        'mobile_allowance': float(financial_impact.mobile_allowance) if financial_impact and financial_impact.mobile_allowance else '',
                        'fuel': float(financial_impact.fuel) if financial_impact and financial_impact.fuel else '',
                        'total': float(financial_impact.total) if financial_impact and financial_impact.total else ''
                    }
                }
            })
        except Employee.DoesNotExist:
            return JsonResponse({'error': 'Employee not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# View for create employee data
class CreateDataView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def post(self, request, department_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                with transaction.atomic():  # 🚀 Start atomic block
                    
                    print(request.POST)
                    step = request.POST.get('step')
                    department = DepartmentTeams.objects.get(
                        id=department_id,
                        company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                    )
                if step == 'employee':
                    employee = Employee.objects.create(
                        fullname=request.POST.get('fullname'),
                        company=department.company,
                        department_team=department,
                        department_group_id=request.POST.get('department_group_id'),
                        section_id=request.POST.get('section_id'),
                        designation_id=request.POST.get('designation_id'),
                        location_id=request.POST.get('location_id'),
                        date_of_joining=request.POST.get('date_of_joining'),
                        resign=request.POST.get('resign') == 'true',
                        date_of_resignation=request.POST.get('date_of_resignation') or None,
                        remarks=request.POST.get('remarks') or '',
                        image=request.FILES.get('image') if 'image' in request.FILES else None
                    )
                    logger.debug(f"Employee created: {employee.emp_id}")
                    return JsonResponse({'message': 'Employee created', 'employee_id': employee.emp_id})
                elif step == 'current_package':
                    employee_id = request.POST.get('employee_id')
                    employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                    current_package = CurrentPackageDetails.objects.create(
                        employee=employee,
                        gross_salary=request.POST.get('gross_salary'),
                        vehicle=request.POST.get('vehicle'),
                        fuel_limit=request.POST.get('fuel_limit'),
                        mobile_allowance=request.POST.get('mobile_allowance')
                    )
                    logger.debug(f"CurrentPackageDetails created for employee: {employee_id}")
                    return JsonResponse({'message': 'Current Package created'})
                elif step == 'proposed_package':
                    employee_id = request.POST.get('employee_id')
                    employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                    proposed_package = ProposedPackageDetails.objects.create(
                        employee=employee,
                        increment_percentage=request.POST.get('increment_percentage'),
                        increased_fuel_amount=request.POST.get('increased_fuel_amount'),
                        mobile_allowance=request.POST.get('mobile_allowance'),
                        vehicle=request.POST.get('vehicle')
                    )
                    logger.debug(f"ProposedPackageDetails created for employee: {employee_id}")
                    return JsonResponse({'message': 'Proposed Package created'})
                elif step == 'financial_impact':
                    employee_id = request.POST.get('employee_id')
                    employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                    financial_impact = FinancialImpactPerMonth.objects.create(
                        employee=employee,
                        emp_status_id=request.POST.get('emp_status_id')
                    )
                    logger.debug(f"FinancialImpactPerMonth created for employee: {employee_id}")
                    return JsonResponse({'message': 'Financial Impact created'})
                return JsonResponse({'error': 'Invalid step'}, status=400)
            except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
                logger.error(f"Error in CreateDataView: {str(e)}")
                return JsonResponse({'error': 'Invalid data'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)


class GetDataView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        return view

    def get(self, request, table, id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
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
                            'fullname': employee.fullname,
                            'department_group_id': employee.department_group_id,
                            'section_id': employee.section_id,
                            'designation_id': employee.designation_id,
                            'location_id': employee.location_id,
                            'date_of_joining': employee.date_of_joining.isoformat() if employee.date_of_joining else '',
                            'resign': employee.resign,
                            'date_of_resignation': employee.date_of_resignation.isoformat() if employee.date_of_resignation else '',
                            'remarks': employee.remarks or '',
                            'image': employee.image.url if employee.image else ''
                        },
                        'current_package': {
                            'gross_salary': str(current_package.gross_salary) if current_package and current_package.gross_salary else '',
                            'vehicle': current_package.vehicle if current_package else '',
                            'fuel_limit': str(current_package.fuel_limit) if current_package and current_package.fuel_limit else '',
                            'mobile_allowance': str(current_package.mobile_allowance) if current_package and current_package.mobile_allowance else ''
                        },
                        'proposed_package': {
                            'increment_percentage': str(proposed_package.increment_percentage) if proposed_package and proposed_package.increment_percentage else '',
                            'increased_amount': str(proposed_package.increased_amount) if proposed_package and proposed_package.increased_amount else '',
                            'revised_salary': str(proposed_package.revised_salary) if proposed_package and proposed_package.revised_salary else '',
                            'increased_fuel_amount': str(proposed_package.increased_fuel_amount) if proposed_package and proposed_package.increased_fuel_amount else '',
                            'revised_fuel_allowance': str(proposed_package.revised_fuel_allowance) if proposed_package and proposed_package.revised_fuel_allowance else '',
                            'mobile_allowance': str(proposed_package.mobile_allowance) if proposed_package and proposed_package.mobile_allowance else '',
                            'vehicle': proposed_package.vehicle if proposed_package else ''
                        },
                        'financial_impact': {
                            'emp_status_id': str(financial_impact.emp_status_id) if financial_impact and financial_impact.emp_status_id else '',
                            'serving_years': str(financial_impact.serving_years) if financial_impact and financial_impact.serving_years else '',
                            'salary': str(financial_impact.salary) if financial_impact and financial_impact.salary else '',
                            'gratuity': str(financial_impact.gratuity) if financial_impact and financial_impact.gratuity else '',
                            'bonus': str(financial_impact.bonus) if financial_impact and financial_impact.bonus else '',
                            'leave_encashment': str(financial_impact.leave_encashment) if financial_impact and financial_impact.leave_encashment else '',
                            'mobile_allowance': str(financial_impact.mobile_allowance) if financial_impact and financial_impact.mobile_allowance else '',
                            'fuel': str(financial_impact.fuel) if financial_impact and financial_impact.fuel else '',
                            'total': str(financial_impact.total) if financial_impact and financial_impact.total else ''
                        }
                    }
                    # logger.debug(f"Fetched data for employee {id}: {data}")
                    return JsonResponse({'data': data})
                return JsonResponse({'error': 'Invalid table'}, status=400)
            except (Employee.DoesNotExist, ValueError) as e:
                # logger.error(f"Error fetching employee {id}: {str(e)}")
                return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)
    

class UpdateDataView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def patch(self, request, department_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                print(data)
                step = data.get('step')
                employee_id = data.get('employee_id')
                department = DepartmentTeams.objects.get(
                    id=department_id,
                    company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                )
                employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                if step == 'employee':
                    employee.fullname = data.get('fullname')
                    employee.department_group_id = data.get('department_group_id')
                    employee.section_id = data.get('section_id')
                    employee.designation_id = data.get('designation_id')
                    employee.location_id = data.get('location_id')
                    employee.date_of_joining = data.get('date_of_joining')
                    employee.resign = data.get('resign') == 'true'
                    employee.date_of_resignation = data.get('date_of_resignation') or None
                    employee.remarks = data.get('remarks') or ''
                    if 'image' in request.FILES:
                        employee.image = request.FILES.get('image')
                    employee.save()
                    logger.debug(f"Employee updated: {employee_id}")
                    return JsonResponse({'message': 'Employee updated', 'employee_id': employee_id})
                elif step == 'current_package':
                    current_package, created = CurrentPackageDetails.objects.get_or_create(employee=employee)
                    current_package.gross_salary = data.get('gross_salary')
                    current_package.vehicle = data.get('vehicle')
                    current_package.fuel_limit = data.get('fuel_limit', None)
                    current_package.mobile_allowance = data.get('mobile_allowance', None)
                    current_package.save()
                    logger.debug(f"CurrentPackageDetails updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Current Package updated'})
                elif step == 'proposed_package':
                    proposed_package, created = ProposedPackageDetails.objects.get_or_create(employee=employee)
                    proposed_package.increment_percentage = data.get('increment_percentage')
                    proposed_package.increased_fuel_amount = data.get('increased_fuel_amount')
                    proposed_package.mobile_allowance = data.get('mobile_allowance')
                    proposed_package.vehicle = data.get('vehicle')
                    proposed_package.save()
                    logger.debug(f"ProposedPackageDetails updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Proposed Package updated'})
                elif step == 'financial_impact':
                    financial_impact, created = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
                    financial_impact.emp_status_id = data.get('emp_status_id')
                    financial_impact.save()
                    logger.debug(f"FinancialImpactPerMonth updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Financial Impact updated'})
                return JsonResponse({'error': 'Invalid step'}, status=400)
            except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
                logger.error(f"Error in UpdateDataView: {str(e)}")
                return JsonResponse({'error': 'Invalid data'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)
    

class DeleteDataView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        return view

    def delete(self, request, table, id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                if table == 'employee':
                    employee = Employee.objects.filter(
                        emp_id=id,
                        department_team__company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                    ).first()
                    if not employee:
                        return JsonResponse({'error': 'Invalid employee'}, status=400)
                    employee.delete()
                    logger.debug(f"Employee deleted: {id}")
                    return JsonResponse({'message': 'Employee deleted successfully'})
                return JsonResponse({'error': 'Invalid table'}, status=400)
            except (Employee.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid data'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)


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
                        'vehicle_type': vehicle.vehicle_type,
                        'label': f"{vehicle.brand.name} {vehicle.model_name} ({vehicle.vehicle_type})"
                    }
                    for vehicle in vehicles
                ]
                return JsonResponse({'data': data})
            except Exception as e:
                return JsonResponse({'error': f'Error fetching vehicles: {str(e)}'}, status=500)
        return JsonResponse({'error': 'Invalid request'}, status=400)















# In app/views.py
from django.shortcuts import render, redirect
from .models import FieldFormula, FieldReference
from .forms import FieldFormulaForm, FormulaForm
from django.apps import apps
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models 


# For Formula CRUD view


class FormulaListView(PermissionRequiredMixin, View):
    permission_required = "user.view_formula"
    template_name = "view_formula.html"

    def get(self, request):
        formulas = Formula.objects.all().order_by('-id')  # latest first
        return render(request, self.template_name, {
            'formulas': formulas
        })


class CreateFormulaView(PermissionRequiredMixin, View):
    permission_required = "user.add_formula"
    template_name = "create_formula.html"

    def get(self, request):
        form = FormulaForm()
        field_references = FieldReference.objects.all()
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references
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
            'field_references': field_references
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
            'formula': formula
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
            'formula': formula
        })



# For Manage Formula CRUD

class FieldFormulaListView(PermissionRequiredMixin, View):
    permission_required = "user.view_fieldformula"
    template_name = "view_field_formulas.html"

    def get(self, request):
        company_data = get_companies_and_department_teams(request.user)
        field_formulas = FieldFormula.objects.all().order_by('-id')
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
        form = FieldFormulaForm()
        field_references = FieldReference.objects.all()
        company_data = get_companies_and_department_teams(request.user)
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references,
            'company_data': company_data
        })

    def post(self, request):
        form = FieldFormulaForm(request.POST)
        field_references = FieldReference.objects.all()
        company_data = get_companies_and_department_teams(request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Field Formula created successfully!")
            return redirect("view_field_formulas")
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
        form = FieldFormulaForm(instance=field_formula)
        field_references = FieldReference.objects.all()
        company_data = get_companies_and_department_teams(request.user)
        return render(request, self.template_name, {
            'form': form,
            'field_references': field_references,
            'company_data': company_data,
            'field_formula': field_formula
        })

    def post(self, request, pk):
        field_formula = get_object_or_404(FieldFormula, pk=pk)
        form = FieldFormulaForm(request.POST, instance=field_formula)
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







































from django.views import View
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import transaction
from .models import (
    Employee, CurrentPackageDetails, ProposedPackageDetails, FinancialImpactPerMonth,
    EmployeeDraft, CurrentPackageDetailsDraft, ProposedPackageDetailsDraft, FinancialImpactPerMonthDraft
)
import json
from decimal import Decimal


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
            drafts_saved = False
            with transaction.atomic():
                for employee_id, tabs in data.items():
                    employee = Employee.objects.filter(emp_id=employee_id, department_team_id=department_id).first()
                    if not employee:
                        return JsonResponse({'error': f'Employee {employee_id} not found'}, status=404)

                    has_changes = False
                    employee_draft_edited = {}
                    current_package_edited = {}
                    proposed_package_edited = {}
                    financial_impact_edited = {}

                    for tab, fields in tabs.items():
                        if tab == 'employee':
                            for field, value in fields.items():
                                if field in ['fullname', 'department_group_id', 'section_id', 'designation_id', 'location_id', 'date_of_joining', 'resign', 'date_of_resignation', 'remarks']:
                                    current_value = getattr(employee, field, None)
                                    if field in ['department_group_id', 'section_id', 'designation_id', 'location_id']:
                                        current_value = getattr(getattr(employee, field, None), 'id', None)
                                    elif field == 'resign':
                                        current_value = str(current_value).lower()
                                    if str(value) != str(current_value):
                                        has_changes = True
                                        employee_draft_edited[field] = True
                        elif tab == 'current_package':
                            for field, value in fields.items():
                                if field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'mobile_allowance']:
                                    current_package = CurrentPackageDetails.objects.filter(employee=employee).first()
                                    current_value = getattr(current_package, field, None) if current_package else None
                                    if field == 'vehicle_id':
                                        current_value = current_value.id if current_value else None
                                    if str(value) != str(current_value):
                                        has_changes = True
                                        current_package_edited[field] = True
                        elif tab == 'proposed_package':
                            for field, value in fields.items():
                                if field in ['increment_percentage', 'increased_fuel_amount', 'mobile_allowance_proposed', 'vehicle_proposed_id']:
                                    proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first()
                                    field_key = 'mobile_allowance' if field == 'mobile_allowance_proposed' else ('vehicle_id' if field == 'vehicle_proposed_id' else field)
                                    current_value = getattr(proposed_package, field_key, None) if proposed_package else None
                                    if field in ['vehicle_proposed_id']:
                                        current_value = current_value.id if current_value else None
                                    if str(value) != str(current_value):
                                        has_changes = True
                                        proposed_package_edited[field_key] = True
                        elif tab == 'financial_impact':
                            for field, value in fields.items():
                                if field == 'emp_status_id':
                                    financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first()
                                    current_value = getattr(financial_impact, 'emp_status_id', None) if financial_impact else None
                                    if str(value) != str(current_value):
                                        has_changes = True
                                        financial_impact_edited[field] = True

                    if not has_changes:
                        continue

                    employee_draft = EmployeeDraft.objects.filter(employee=employee).first()
                    if employee_draft_edited or current_package_edited or proposed_package_edited or financial_impact_edited:
                        if not employee_draft:
                            employee_draft = EmployeeDraft(employee=employee, company=employee.company, department_team=employee.department_team)
                        for field, value in tabs.get('employee', {}).items():
                            if field in ['fullname', 'department_group_id', 'section_id', 'designation_id', 'location_id', 'date_of_joining', 'resign', 'date_of_resignation', 'remarks'] and employee_draft_edited.get(field):
                                if field == 'department_group_id':
                                    employee_draft.department_group_id = int(value) if value else None
                                elif field == 'section_id':
                                    employee_draft.section_id = int(value) if value else None
                                elif field == 'designation_id':
                                    employee_draft.designation_id = int(value) if value else None
                                elif field == 'location_id':
                                    employee_draft.location_id = int(value) if value else None
                                elif field == 'resign':
                                    employee_draft.resign = value == 'true'
                                elif field == 'date_of_joining' or field == 'date_of_resignation':
                                    employee_draft.__setattr__(field, value or None)
                                elif field == 'fullname' or field == 'remarks':
                                    employee_draft.__setattr__(field, value or None)
                        employee_draft.edited_fields = employee_draft_edited
                        if employee_draft_edited:
                            employee_draft.save()
                            drafts_saved = True

                    if current_package_edited:
                        draft, created = CurrentPackageDetailsDraft.objects.get_or_create(employee_draft=employee_draft)
                        for field, value in tabs.get('current_package', {}).items():
                            if field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'mobile_allowance'] and current_package_edited.get(field):
                                if field == 'vehicle_id':
                                    draft.vehicle_id = int(value) if value else None
                                elif field in ['gross_salary', 'fuel_limit', 'mobile_allowance']:
                                    draft.__setattr__(field, Decimal(value) if value else Decimal('0'))
                        draft.edited_fields = current_package_edited
                        draft.save()
                        drafts_saved = True

                    if proposed_package_edited:
                        draft, created = ProposedPackageDetailsDraft.objects.get_or_create(employee_draft=employee_draft)
                        for field, value in tabs.get('proposed_package', {}).items():
                            if field in ['increment_percentage', 'increased_fuel_amount', 'mobile_allowance_proposed', 'vehicle_proposed_id'] and proposed_package_edited.get('vehicle_id' if field == 'vehicle_proposed_id' else field):
                                if field == 'vehicle_proposed_id':
                                    draft.vehicle_id = int(value) if value else None
                                elif field == 'mobile_allowance_proposed':
                                    draft.mobile_allowance = Decimal(value) if value else Decimal('0')
                                elif field in ['increment_percentage', 'increased_fuel_amount']:
                                    draft.__setattr__(field, Decimal(value) if value else Decimal('0'))
                        draft.edited_fields = proposed_package_edited
                        draft.save()
                        drafts_saved = True

                    if financial_impact_edited:
                        draft, created = FinancialImpactPerMonthDraft.objects.get_or_create(employee_draft=employee_draft)
                        for field, value in tabs.get('financial_impact', {}).items():
                            if field == 'emp_status_id' and financial_impact_edited.get(field):
                                draft.emp_status_id = int(value) if value else None
                        draft.edited_fields = financial_impact_edited
                        draft.save()
                        drafts_saved = True

                if drafts_saved:
                    return JsonResponse({'message': 'Draft saved'})
                else:
                    return JsonResponse({'message': 'No changes to save'}, status=200)
        except Exception as e:
            print("error: ", e)
            return JsonResponse({'error': str(e)}, status=500)

class SaveFinalView(View):
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
            updated_employees = []
            with transaction.atomic():
                for employee_id, tabs in data.items():
                    employee = Employee.objects.filter(emp_id=employee_id, department_team_id=department_id).first()
                    if not employee:
                        return JsonResponse({'error': f'Employee {employee_id} not found'}, status=404)

                    employee_draft = EmployeeDraft.objects.filter(employee=employee).first()
                    if employee_draft and employee_draft.edited_fields:  # Only process if draft has edited fields
                        for tab, fields in tabs.items():
                            if tab == 'employee':
                                for field, value in fields.items():
                                    if field in ['fullname', 'department_group_id', 'section_id', 'designation_id', 'location_id', 'date_of_joining', 'resign', 'date_of_resignation', 'remarks']:
                                        if field == 'department_group_id':
                                            employee.department_group_id = int(value) if value else None
                                        elif field == 'section_id':
                                            employee.section_id = int(value) if value else None
                                        elif field == 'designation_id':
                                            employee.designation_id = int(value) if value else None
                                        elif field == 'location_id':
                                            employee.location_id = int(value) if value else None
                                        elif field == 'resign':
                                            employee.resign = value == 'true'
                                        elif field == 'date_of_joining' or field == 'date_of_resignation':
                                            employee.__setattr__(field, value or None)
                                        elif field == 'fullname' or field == 'remarks':
                                            employee.__setattr__(field, value or None)
                                employee.save()

                            elif tab == 'current_package':
                                current_package, created = CurrentPackageDetails.objects.get_or_create(employee=employee)
                                for field, value in fields.items():
                                    if field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'mobile_allowance']:
                                        if field == 'vehicle_id':
                                            current_package.vehicle_id = int(value) if value else None
                                        elif field in ['gross_salary', 'fuel_limit', 'mobile_allowance']:
                                            current_package.__setattr__(field, Decimal(value) if value else Decimal('0'))
                                current_package.save()

                            elif tab == 'proposed_package':
                                proposed_package, created = ProposedPackageDetails.objects.get_or_create(employee=employee)
                                for field, value in fields.items():
                                    if field in ['increment_percentage', 'increased_fuel_amount', 'mobile_allowance_proposed', 'vehicle_proposed_id']:
                                        if field == 'vehicle_proposed_id':
                                            proposed_package.vehicle_id = int(value) if value else None
                                        elif field == 'mobile_allowance_proposed':
                                            proposed_package.mobile_allowance = Decimal(value) if value else Decimal('0')
                                        elif field in ['increment_percentage', 'increased_fuel_amount']:
                                            proposed_package.__setattr__(field, Decimal(value) if value else Decimal('0'))
                                proposed_package.save()

                            elif tab == 'financial_impact':
                                financial_impact, created = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
                                for field, value in fields.items():
                                    if field == 'emp_status_id':
                                        financial_impact.emp_status_id = int(value) if value else None
                                financial_impact.save()

                        updated_employees.append(employee_id)
                        employee_draft.delete()

                if updated_employees:
                    EmployeeDraft.objects.filter(employee__department_team_id=department_id).delete()
                    return JsonResponse({'message': 'Changes saved'})
                else:
                    return JsonResponse({'message': 'No changes to save'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
