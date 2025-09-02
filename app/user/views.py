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
    Formula,
    EmployeeDraft,
    CurrentPackageDetailsDraft,
    ProposedPackageDetailsDraft,
    FinancialImpactPerMonthDraft,
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
from django.contrib.auth.decorators import login_required , permission_required
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


# class DepartmentTableView(View):
#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, department_id):
#         # Fetch department with permission check
#         department = DepartmentTeams.objects.filter(
#             id=department_id,
#             company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#         ).first()
#         if not department:
#             return render(request, 'error.html', {'error': 'Invalid department'}, status=400)

#         # Get company data
#         company_data = get_companies_and_department_teams(request.user)

#         # Fetch employees with related data
#         employees = Employee.objects.filter(department_team=department).select_related(
#             'company', 'department_team', 'department_group', 'section', 'designation', 'location'
#         ).prefetch_related('currentpackagedetails', 'proposedpackagedetails', 'financialimpactpermonth', 'drafts')

#         employee_data = []
#         draft_data = {}
#         for emp in employees:
#             print(emp.drafts.first())
#             emp_draft = emp.drafts.first()
#             is_draft = bool(emp_draft)
#             print(is_draft)
#             data = {
#                 'emp_id': emp.emp_id,
#                 'fullname': emp_draft.fullname if is_draft and emp_draft.edited_fields.get('fullname') else emp.fullname,
#                 'company': emp.company,
#                 'department_team': emp.department_team,
#                 'department_group': emp_draft.department_group if is_draft and emp_draft.edited_fields.get('department_group_id') else emp.department_group,
#                 'section': emp_draft.section if is_draft and emp_draft.edited_fields.get('section_id') else emp.section,
#                 'designation': emp_draft.designation if is_draft and emp_draft.edited_fields.get('designation_id') else emp.designation,
#                 'location': emp_draft.location if is_draft and emp_draft.edited_fields.get('location_id') else emp.location,
#                 'date_of_joining': emp_draft.date_of_joining if is_draft and emp_draft.edited_fields.get('date_of_joining') else emp.date_of_joining,
#                 'resign': emp_draft.resign if is_draft and emp_draft.edited_fields.get('resign') else emp.resign,
#                 'date_of_resignation': emp_draft.date_of_resignation if is_draft and emp_draft.edited_fields.get('date_of_resignation') else emp.date_of_resignation,
#                 'remarks': emp_draft.remarks if is_draft and emp_draft.edited_fields.get('remarks') else emp.remarks,
#                 'is_draft': is_draft,
#                 'currentpackagedetails': None,
#                 'proposedpackagedetails': None,
#                 'financialimpactpermonth': None,
#             }
            
#             draft_data[emp.emp_id] = {'employee': {}, 'current_package': {}, 'proposed_package': {}, 'financial_impact': {}}
#             if is_draft:
#                 for field in ['fullname', 'department_group_id', 'section_id', 'designation_id', 'location_id', 'date_of_joining', 'resign', 'date_of_resignation', 'remarks']:
#                     if emp_draft.edited_fields.get(field):
#                         draft_data[emp.emp_id]['employee'][field] = True
            
#             # Current Package
#             current_draft = emp_draft.current_package_drafts.first() if is_draft else None
#             current_package = emp.currentpackagedetails or current_draft
#             if current_package:
#                 data['currentpackagedetails'] = {
#                     'gross_salary': current_draft.gross_salary if is_draft and current_draft and current_draft.edited_fields.get('gross_salary') else current_package.gross_salary,
#                     'vehicle': current_draft.vehicle if is_draft and current_draft and current_draft.edited_fields.get('vehicle_id') else current_package.vehicle,
#                     'fuel_limit': current_draft.fuel_limit if is_draft and current_draft and current_draft.edited_fields.get('fuel_limit') else current_package.fuel_limit,
#                     'mobile_allowance': current_draft.mobile_allowance if is_draft and current_draft and current_draft.edited_fields.get('mobile_allowance') else current_package.mobile_allowance,
#                 }
#                 if is_draft and current_draft:
#                     for field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'mobile_allowance']:
#                         if current_draft.edited_fields.get(field):
#                             draft_data[emp.emp_id]['current_package'][field] = True
            
#             # Proposed Package
#             proposed_draft = emp_draft.proposed_package_drafts.first() if is_draft else None
#             proposed_package = emp.proposedpackagedetails or proposed_draft
#             if proposed_package:
#                 data['proposedpackagedetails'] = {
#                     'increment_percentage': proposed_draft.increment_percentage if is_draft and proposed_draft and proposed_draft.edited_fields.get('increment_percentage') else proposed_package.increment_percentage,
#                     'increased_amount': proposed_package.increased_amount,
#                     'revised_salary': proposed_package.revised_salary,
#                     'increased_fuel_amount': proposed_draft.increased_fuel_amount if is_draft and proposed_draft and proposed_draft.edited_fields.get('increased_fuel_amount') else proposed_package.increased_fuel_amount,
#                     'revised_fuel_allowance': proposed_package.revised_fuel_allowance,
#                     'mobile_allowance': proposed_draft.mobile_allowance if is_draft and proposed_draft and proposed_draft.edited_fields.get('mobile_allowance') else proposed_package.mobile_allowance,
#                     'vehicle': proposed_draft.vehicle if is_draft and proposed_draft and proposed_draft.edited_fields.get('vehicle_id') else proposed_package.vehicle,
#                 }
#                 if is_draft and proposed_draft:
#                     for field in ['increment_percentage', 'increased_fuel_amount', 'mobile_allowance', 'vehicle_id']:
#                         if proposed_draft.edited_fields.get(field):
#                             draft_data[emp.emp_id]['proposed_package'][field] = True
            
#             # Financial Impact
#             financial_draft = emp_draft.financial_impact_drafts.first() if is_draft else None
#             financial_package = emp.financialimpactpermonth or financial_draft
#             if financial_package:
#                 data['financialimpactpermonth'] = {
#                     'emp_status': financial_draft.emp_status if is_draft and financial_draft and financial_draft.edited_fields.get('emp_status_id') else financial_package.emp_status,
#                     'serving_years': financial_package.serving_years,
#                     'salary': financial_package.salary,
#                     'gratuity': financial_package.gratuity,
#                     'bonus': financial_package.bonus,
#                     'leave_encashment': financial_package.leave_encashment,
#                     'mobile_allowance': financial_package.mobile_allowance,
#                     'fuel': financial_package.fuel,
#                     'total': financial_package.total,
#                 }
#                 if is_draft and financial_draft:
#                     if financial_draft.edited_fields.get('emp_status_id'):
#                         draft_data[emp.emp_id]['financial_impact']['emp_status_id'] = True
            
#             employee_data.append(data)
        
#         return render(request, 'department_table.html', {
#             'department': department,
#             'employees': employee_data,
#             'department_id': department_id,
#             'company_data': company_data,
#             'draft_data': draft_data
#         })


# class GetEmployeeDataView(View):
#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, employee_id):
#         try:
#             employee = Employee.objects.get(emp_id=employee_id)
#             current_package = CurrentPackageDetails.objects.filter(employee=employee).first()
#             proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first()
#             financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first()

#             return JsonResponse({
#                 'data': {
#                     'employee': {
#                         'fullname': employee.fullname,
#                         'department_group_id': employee.department_group.id if employee.department_group else None,
#                         'section_id': employee.section.id if employee.section else None,
#                         'designation_id': employee.designation.id if employee.designation else None,
#                         'location_id': employee.location.id if employee.location else None,
#                         'date_of_joining': employee.date_of_joining.strftime('%Y-%m-%d') if employee.date_of_joining else '',
#                         'resign': employee.resign,
#                         'date_of_resignation': employee.date_of_resignation.strftime('%Y-%m-%d') if employee.date_of_resignation else '',
#                         'remarks': employee.remarks or ''
#                     },
#                     'current_package': {
#                         'gross_salary': float(current_package.gross_salary) if current_package and current_package.gross_salary else '',
#                         'vehicle_id': current_package.vehicle.id if current_package and current_package.vehicle else '',
#                         'fuel_limit': float(current_package.fuel_limit) if current_package and current_package.fuel_limit else '',
#                         'mobile_allowance': float(current_package.mobile_allowance) if current_package and current_package.mobile_allowance else ''
#                     },
#                     'proposed_package': {
#                         'increment_percentage': float(proposed_package.increment_percentage) if proposed_package and proposed_package.increment_percentage else '',
#                         'increased_amount': float(proposed_package.increased_amount) if proposed_package and proposed_package.increased_amount else '',
#                         'revised_salary': float(proposed_package.revised_salary) if proposed_package and proposed_package.revised_salary else '',
#                         'increased_fuel_amount': float(proposed_package.increased_fuel_amount) if proposed_package and proposed_package.increased_fuel_amount else '',
#                         'revised_fuel_allowance': float(proposed_package.revised_fuel_allowance) if proposed_package and proposed_package.revised_fuel_allowance else '',
#                         'mobile_allowance': float(proposed_package.mobile_allowance) if proposed_package and proposed_package.mobile_allowance else '',
#                         'vehicle_id': proposed_package.vehicle.id if proposed_package and proposed_package.vehicle else ''
#                     },
#                     'financial_impact': {
#                         'emp_status_id': financial_impact.emp_status.id if financial_impact and financial_impact.emp_status else '',
#                         'serving_years': financial_impact.serving_years if financial_impact else '',
#                         'salary': float(financial_impact.salary) if financial_impact and financial_impact.salary else '',
#                         'gratuity': float(financial_impact.gratuity) if financial_impact and financial_impact.gratuity else '',
#                         'bonus': float(financial_impact.bonus) if financial_impact and financial_impact.bonus else '',
#                         'leave_encashment': float(financial_impact.leave_encashment) if financial_impact and financial_impact.leave_encashment else '',
#                         'mobile_allowance': float(financial_impact.mobile_allowance) if financial_impact and financial_impact.mobile_allowance else '',
#                         'fuel': float(financial_impact.fuel) if financial_impact and financial_impact.fuel else '',
#                         'total': float(financial_impact.total) if financial_impact and financial_impact.total else ''
#                     }
#                 }
#             })
#         except Employee.DoesNotExist:
#             return JsonResponse({'error': 'Employee not found'}, status=404)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)


# # View for create employee data
# class CreateDataView(View):
#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def post(self, request, department_id):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             try:
#                 with transaction.atomic():  # 🚀 Start atomic block
                    
#                     print(request.POST)
#                     step = request.POST.get('step')
#                     department = DepartmentTeams.objects.get(
#                         id=department_id,
#                         company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                     )
#                 if step == 'employee':
#                     employee = Employee.objects.create(
#                         fullname=request.POST.get('fullname'),
#                         company=department.company,
#                         department_team=department,
#                         department_group_id=request.POST.get('department_group_id'),
#                         section_id=request.POST.get('section_id'),
#                         designation_id=request.POST.get('designation_id'),
#                         location_id=request.POST.get('location_id'),
#                         date_of_joining=request.POST.get('date_of_joining'),
#                         resign=request.POST.get('resign') == 'true',
#                         date_of_resignation=request.POST.get('date_of_resignation') or None,
#                         remarks=request.POST.get('remarks') or '',
#                         image=request.FILES.get('image') if 'image' in request.FILES else None
#                     )
#                     logger.debug(f"Employee created: {employee.emp_id}")
#                     return JsonResponse({'message': 'Employee created', 'employee_id': employee.emp_id})
#                 elif step == 'current_package':
#                     employee_id = request.POST.get('employee_id')
#                     employee = Employee.objects.get(emp_id=employee_id, department_team=department)
#                     current_package = CurrentPackageDetails.objects.create(
#                         employee=employee,
#                         gross_salary=request.POST.get('gross_salary'),
#                         vehicle=request.POST.get('vehicle'),
#                         fuel_limit=request.POST.get('fuel_limit'),
#                         mobile_allowance=request.POST.get('mobile_allowance')
#                     )
#                     logger.debug(f"CurrentPackageDetails created for employee: {employee_id}")
#                     return JsonResponse({'message': 'Current Package created'})
#                 elif step == 'proposed_package':
#                     employee_id = request.POST.get('employee_id')
#                     employee = Employee.objects.get(emp_id=employee_id, department_team=department)
#                     proposed_package = ProposedPackageDetails.objects.create(
#                         employee=employee,
#                         increment_percentage=request.POST.get('increment_percentage'),
#                         increased_fuel_amount=request.POST.get('increased_fuel_amount'),
#                         mobile_allowance=request.POST.get('mobile_allowance'),
#                         vehicle=request.POST.get('vehicle')
#                     )
#                     logger.debug(f"ProposedPackageDetails created for employee: {employee_id}")
#                     return JsonResponse({'message': 'Proposed Package created'})
#                 elif step == 'financial_impact':
#                     employee_id = request.POST.get('employee_id')
#                     employee = Employee.objects.get(emp_id=employee_id, department_team=department)
#                     financial_impact = FinancialImpactPerMonth.objects.create(
#                         employee=employee,
#                         emp_status_id=request.POST.get('emp_status_id')
#                     )
#                     logger.debug(f"FinancialImpactPerMonth created for employee: {employee_id}")
#                     return JsonResponse({'message': 'Financial Impact created'})
#                 return JsonResponse({'error': 'Invalid step'}, status=400)
#             except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
#                 logger.error(f"Error in CreateDataView: {str(e)}")
#                 return JsonResponse({'error': 'Invalid data'}, status=400)
#         return JsonResponse({'error': 'Invalid request'}, status=400)


# class GetDataView(View):
#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         return view

#     def get(self, request, table, id):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             try:
#                 if table == 'employee':
#                     logger.debug(f"Fetching employee with emp_id: {id}")
#                     employee = Employee.objects.filter(
#                         emp_id=id,
#                         department_team__company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                     ).first()
#                     if not employee:
#                         logger.error(f"Employee with emp_id {id} not found or not authorized")
#                         return JsonResponse({'error': f'Employee with ID {id} not found'}, status=404)
#                     current_package = CurrentPackageDetails.objects.filter(employee=employee).first() or {}
#                     proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first() or {}
#                     financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first() or {}
#                     data = {
#                         'employee': {
#                             'fullname': employee.fullname,
#                             'department_group_id': employee.department_group_id,
#                             'section_id': employee.section_id,
#                             'designation_id': employee.designation_id,
#                             'location_id': employee.location_id,
#                             'date_of_joining': employee.date_of_joining.isoformat() if employee.date_of_joining else '',
#                             'resign': employee.resign,
#                             'date_of_resignation': employee.date_of_resignation.isoformat() if employee.date_of_resignation else '',
#                             'remarks': employee.remarks or '',
#                             'image': employee.image.url if employee.image else ''
#                         },
#                         'current_package': {
#                             'gross_salary': str(current_package.gross_salary) if current_package and current_package.gross_salary else '',
#                             'vehicle': current_package.vehicle if current_package else '',
#                             'fuel_limit': str(current_package.fuel_limit) if current_package and current_package.fuel_limit else '',
#                             'mobile_allowance': str(current_package.mobile_allowance) if current_package and current_package.mobile_allowance else ''
#                         },
#                         'proposed_package': {
#                             'increment_percentage': str(proposed_package.increment_percentage) if proposed_package and proposed_package.increment_percentage else '',
#                             'increased_amount': str(proposed_package.increased_amount) if proposed_package and proposed_package.increased_amount else '',
#                             'revised_salary': str(proposed_package.revised_salary) if proposed_package and proposed_package.revised_salary else '',
#                             'increased_fuel_amount': str(proposed_package.increased_fuel_amount) if proposed_package and proposed_package.increased_fuel_amount else '',
#                             'revised_fuel_allowance': str(proposed_package.revised_fuel_allowance) if proposed_package and proposed_package.revised_fuel_allowance else '',
#                             'mobile_allowance': str(proposed_package.mobile_allowance) if proposed_package and proposed_package.mobile_allowance else '',
#                             'vehicle': proposed_package.vehicle if proposed_package else ''
#                         },
#                         'financial_impact': {
#                             'emp_status_id': str(financial_impact.emp_status_id) if financial_impact and financial_impact.emp_status_id else '',
#                             'serving_years': str(financial_impact.serving_years) if financial_impact and financial_impact.serving_years else '',
#                             'salary': str(financial_impact.salary) if financial_impact and financial_impact.salary else '',
#                             'gratuity': str(financial_impact.gratuity) if financial_impact and financial_impact.gratuity else '',
#                             'bonus': str(financial_impact.bonus) if financial_impact and financial_impact.bonus else '',
#                             'leave_encashment': str(financial_impact.leave_encashment) if financial_impact and financial_impact.leave_encashment else '',
#                             'mobile_allowance': str(financial_impact.mobile_allowance) if financial_impact and financial_impact.mobile_allowance else '',
#                             'fuel': str(financial_impact.fuel) if financial_impact and financial_impact.fuel else '',
#                             'total': str(financial_impact.total) if financial_impact and financial_impact.total else ''
#                         }
#                     }
#                     # logger.debug(f"Fetched data for employee {id}: {data}")
#                     return JsonResponse({'data': data})
#                 return JsonResponse({'error': 'Invalid table'}, status=400)
#             except (Employee.DoesNotExist, ValueError) as e:
#                 # logger.error(f"Error fetching employee {id}: {str(e)}")
#                 return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)
#         return JsonResponse({'error': 'Invalid request'}, status=400)
    

# class UpdateDataView(View):
#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def patch(self, request, department_id):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             try:
#                 data = json.loads(request.body)
#                 print(data)
#                 step = data.get('step')
#                 employee_id = data.get('employee_id')
#                 department = DepartmentTeams.objects.get(
#                     id=department_id,
#                     company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                 )
#                 employee = Employee.objects.get(emp_id=employee_id, department_team=department)
#                 if step == 'employee':
#                     employee.fullname = data.get('fullname')
#                     employee.department_group_id = data.get('department_group_id')
#                     employee.section_id = data.get('section_id')
#                     employee.designation_id = data.get('designation_id')
#                     employee.location_id = data.get('location_id')
#                     employee.date_of_joining = data.get('date_of_joining')
#                     employee.resign = data.get('resign') == 'true'
#                     employee.date_of_resignation = data.get('date_of_resignation') or None
#                     employee.remarks = data.get('remarks') or ''
#                     if 'image' in request.FILES:
#                         employee.image = request.FILES.get('image')
#                     employee.save()
#                     logger.debug(f"Employee updated: {employee_id}")
#                     return JsonResponse({'message': 'Employee updated', 'employee_id': employee_id})
#                 elif step == 'current_package':
#                     current_package, created = CurrentPackageDetails.objects.get_or_create(employee=employee)
#                     current_package.gross_salary = data.get('gross_salary')
#                     current_package.vehicle = data.get('vehicle')
#                     current_package.fuel_limit = data.get('fuel_limit', None)
#                     current_package.mobile_allowance = data.get('mobile_allowance', None)
#                     current_package.save()
#                     logger.debug(f"CurrentPackageDetails updated for employee: {employee_id}")
#                     return JsonResponse({'message': 'Current Package updated'})
#                 elif step == 'proposed_package':
#                     proposed_package, created = ProposedPackageDetails.objects.get_or_create(employee=employee)
#                     proposed_package.increment_percentage = data.get('increment_percentage')
#                     proposed_package.increased_fuel_amount = data.get('increased_fuel_amount')
#                     proposed_package.mobile_allowance = data.get('mobile_allowance')
#                     proposed_package.vehicle = data.get('vehicle')
#                     proposed_package.save()
#                     logger.debug(f"ProposedPackageDetails updated for employee: {employee_id}")
#                     return JsonResponse({'message': 'Proposed Package updated'})
#                 elif step == 'financial_impact':
#                     financial_impact, created = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
#                     financial_impact.emp_status_id = data.get('emp_status_id')
#                     financial_impact.save()
#                     logger.debug(f"FinancialImpactPerMonth updated for employee: {employee_id}")
#                     return JsonResponse({'message': 'Financial Impact updated'})
#                 return JsonResponse({'error': 'Invalid step'}, status=400)
#             except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
#                 logger.error(f"Error in UpdateDataView: {str(e)}")
#                 return JsonResponse({'error': 'Invalid data'}, status=400)
#         return JsonResponse({'error': 'Invalid request'}, status=400)
    

# class DeleteDataView(View):
#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         return view

#     def delete(self, request, table, id):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             try:
#                 if table == 'employee':
#                     employee = Employee.objects.filter(
#                         emp_id=id,
#                         department_team__company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                     ).first()
#                     if not employee:
#                         return JsonResponse({'error': 'Invalid employee'}, status=400)
#                     employee.delete()
#                     logger.debug(f"Employee deleted: {id}")
#                     return JsonResponse({'message': 'Employee deleted successfully'})
#                 return JsonResponse({'error': 'Invalid table'}, status=400)
#             except (Employee.DoesNotExist, ValueError):
#                 return JsonResponse({'error': 'Invalid data'}, status=400)
#         return JsonResponse({'error': 'Invalid request'}, status=400)


'''
Separate view of dept table
'''

# class DepartmentTableView(View):
#     template_name = 'dept_table_list.html'

#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, department_id):
#         department = DepartmentTeams.objects.filter(
#             id=department_id,
#             company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#         ).first()
#         if not department:
#             return render(request, 'error.html', {'error': 'Invalid department'}, status=400)

#         company_data = get_companies_and_department_teams(request.user)
#         employees = Employee.objects.filter(department_team=department).select_related(
#             'company', 'department_team', 'department_group', 'section', 'designation', 'location'
#         ).prefetch_related('currentpackagedetails', 'proposedpackagedetails', 'financialimpactpermonth', 'drafts')

#         employee_data = []
#         draft_data = {}
#         for emp in employees:
#             emp_draft = emp.drafts.first()
#             is_draft = bool(emp_draft)
#             data = {
#                 'emp_id': emp.emp_id,
#                 'fullname': emp_draft.fullname if is_draft and emp_draft.edited_fields.get('fullname') else emp.fullname,
#                 'company': emp.company,
#                 'department_team': emp.department_team,
#                 'department_group': emp_draft.department_group if is_draft and emp_draft.edited_fields.get('department_group_id') else emp.department_group,
#                 'section': emp_draft.section if is_draft and emp_draft.edited_fields.get('section_id') else emp.section,
#                 'designation': emp_draft.designation if is_draft and emp_draft.edited_fields.get('designation_id') else emp.designation,
#                 'location': emp_draft.location if is_draft and emp_draft.edited_fields.get('location_id') else emp.location,
#                 'date_of_joining': emp_draft.date_of_joining if is_draft and emp_draft.edited_fields.get('date_of_joining') else emp.date_of_joining,
#                 'resign': emp_draft.resign if is_draft and emp_draft.edited_fields.get('resign') else emp.resign,
#                 'date_of_resignation': emp_draft.date_of_resignation if is_draft and emp_draft.edited_fields.get('date_of_resignation') else emp.date_of_resignation,
#                 'remarks': emp_draft.remarks if is_draft and emp_draft.edited_fields.get('remarks') else emp.remarks,
#                 'is_draft': is_draft,
#                 'currentpackagedetails': None,
#                 'proposedpackagedetails': None,
#                 'financialimpactpermonth': None,
#             }
#             draft_data[emp.emp_id] = {'employee': {}, 'current_package': {}, 'proposed_package': {}, 'financial_impact': {}}
#             if is_draft:
#                 for field in ['fullname', 'department_group_id', 'section_id', 'designation_id', 'location_id', 'date_of_joining', 'resign', 'date_of_resignation', 'remarks']:
#                     if emp_draft.edited_fields.get(field):
#                         draft_data[emp.emp_id]['employee'][field] = True

#             current_draft = emp_draft.current_package_drafts.first() if is_draft else None
#             current_package = emp.currentpackagedetails or current_draft
#             if current_package:
#                 data['currentpackagedetails'] = {
#                     'gross_salary': current_draft.gross_salary if is_draft and current_draft and current_draft.edited_fields.get('gross_salary') else current_package.gross_salary,
#                     'vehicle': current_draft.vehicle if is_draft and current_draft and current_draft.edited_fields.get('vehicle_id') else current_package.vehicle,
#                     'fuel_limit': current_draft.fuel_limit if is_draft and current_draft and current_draft.edited_fields.get('fuel_limit') else current_package.fuel_limit,
#                     'mobile_allowance': current_draft.mobile_allowance if is_draft and current_draft and current_draft.edited_fields.get('mobile_allowance') else current_package.mobile_allowance,
#                 }
#                 if is_draft and current_draft:
#                     for field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'mobile_allowance']:
#                         if current_draft.edited_fields.get(field):
#                             draft_data[emp.emp_id]['current_package'][field] = True

#             proposed_draft = emp_draft.proposed_package_drafts.first() if is_draft else None
#             proposed_package = emp.proposedpackagedetails or proposed_draft
#             if proposed_package:
#                 data['proposedpackagedetails'] = {
#                     'increment_percentage': proposed_draft.increment_percentage if is_draft and proposed_draft and proposed_draft.edited_fields.get('increment_percentage') else proposed_package.increment_percentage,
#                     'increased_amount': proposed_package.increased_amount,
#                     'revised_salary': proposed_package.revised_salary,
#                     'increased_fuel_amount': proposed_draft.increased_fuel_amount if is_draft and proposed_draft and proposed_draft.edited_fields.get('increased_fuel_amount') else proposed_package.increased_fuel_amount,
#                     'revised_fuel_allowance': proposed_package.revised_fuel_allowance,
#                     'mobile_allowance': proposed_draft.mobile_allowance if is_draft and proposed_draft and proposed_draft.edited_fields.get('mobile_allowance') else proposed_package.mobile_allowance,
#                     'vehicle': proposed_draft.vehicle if is_draft and proposed_draft and proposed_draft.edited_fields.get('vehicle_id') else proposed_package.vehicle,
#                 }
#                 if is_draft and proposed_draft:
#                     for field in ['increment_percentage', 'increased_fuel_amount', 'mobile_allowance', 'vehicle_id']:
#                         if proposed_draft.edited_fields.get(field):
#                             draft_data[emp.emp_id]['proposed_package'][field] = True

#             financial_draft = emp_draft.financial_impact_drafts.first() if is_draft else None
#             print("hello")
#             financial_package, _ = FinancialImpactPerMonth.objects.get_or_create(employee=emp)
#             financial_package = financial_draft or financial_package
#             if financial_package:
#                 data['financialimpactpermonth'] = {
#                     'emp_status': financial_draft.emp_status if is_draft and financial_draft and financial_draft.edited_fields.get('emp_status_id') else financial_package.emp_status,
#                     'serving_years': financial_package.serving_years,
#                     'salary': financial_package.salary,
#                     'gratuity': financial_package.gratuity,
#                     'bonus': financial_package.bonus,
#                     'leave_encashment': financial_package.leave_encashment,
#                     'mobile_allowance': financial_package.mobile_allowance,
#                     'fuel': financial_package.fuel,
#                     'total': financial_package.total,
#                 }
#                 if is_draft and financial_draft:
#                     if financial_draft.edited_fields.get('emp_status_id'):
#                         draft_data[emp.emp_id]['financial_impact']['emp_status_id'] = True

#             employee_data.append(data)

#         return render(request, self.template_name, {
#             'department': department,
#             'employees': employee_data,
#             'department_id': department_id,
#             'company_data': company_data,
#             'draft_data': draft_data
#         })

# class GetEmployeeDataView(View):
#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, employee_id):
#         try:
#             employee = Employee.objects.get(emp_id=employee_id)
#             current_package = CurrentPackageDetails.objects.filter(employee=employee).first()
#             proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first()
#             financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first()

#             return JsonResponse({
#                 'data': {
#                     'employee': {
#                         'fullname': employee.fullname,
#                         'department_group_id': employee.department_group.id if employee.department_group else None,
#                         'section_id': employee.section.id if employee.section else None,
#                         'designation_id': employee.designation.id if employee.designation else None,
#                         'location_id': employee.location.id if employee.location else None,
#                         'date_of_joining': employee.date_of_joining.strftime('%Y-%m-%d') if employee.date_of_joining else '',
#                         'resign': employee.resign,
#                         'date_of_resignation': employee.date_of_resignation.strftime('%Y-%m-%d') if employee.date_of_resignation else '',
#                         'remarks': employee.remarks or ''
#                     },
#                     'current_package': {
#                         'gross_salary': float(current_package.gross_salary) if current_package and current_package.gross_salary else '',
#                         'vehicle_id': current_package.vehicle.id if current_package and current_package.vehicle else '',
#                         'fuel_limit': float(current_package.fuel_limit) if current_package and current_package.fuel_limit else '',
#                         'mobile_allowance': float(current_package.mobile_allowance) if current_package and current_package.mobile_allowance else ''
#                     },
#                     'proposed_package': {
#                         'increment_percentage': float(proposed_package.increment_percentage) if proposed_package and proposed_package.increment_percentage else '',
#                         'increased_amount': float(proposed_package.increased_amount) if proposed_package and proposed_package.increased_amount else '',
#                         'revised_salary': float(proposed_package.revised_salary) if proposed_package and proposed_package.revised_salary else '',
#                         'increased_fuel_amount': float(proposed_package.increased_fuel_amount) if proposed_package and proposed_package.increased_fuel_amount else '',
#                         'revised_fuel_allowance': float(proposed_package.revised_fuel_allowance) if proposed_package and proposed_package.revised_fuel_allowance else '',
#                         'mobile_allowance': float(proposed_package.mobile_allowance) if proposed_package and proposed_package.mobile_allowance else '',
#                         'vehicle_id': proposed_package.vehicle.id if proposed_package and proposed_package.vehicle else ''
#                     },
#                     'financial_impact': {
#                         'emp_status_id': financial_impact.emp_status.id if financial_impact and financial_impact.emp_status else '',
#                         'serving_years': financial_impact.serving_years if financial_impact else '',
#                         'salary': float(financial_impact.salary) if financial_impact and financial_impact.salary else '',
#                         'gratuity': float(financial_impact.gratuity) if financial_impact and financial_impact.gratuity else '',
#                         'bonus': float(financial_impact.bonus) if financial_impact and financial_impact.bonus else '',
#                         'leave_encashment': float(financial_impact.leave_encashment) if financial_impact and financial_impact.leave_encashment else '',
#                         'mobile_allowance': float(financial_impact.mobile_allowance) if financial_impact and financial_impact.mobile_allowance else '',
#                         'fuel': float(financial_impact.fuel) if financial_impact and financial_impact.fuel else '',
#                         'total': float(financial_impact.total) if financial_impact and financial_impact.total else ''
#                     }
#                 }
#             })
#         except Employee.DoesNotExist:
#             return JsonResponse({'error': 'Employee not found'}, status=404)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)

# class CreateEmployeeView(View):
#     template_name = 'create_dept_table.html'

#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = permission_required('user.add_employee', raise_exception=True)(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, department_id):
#         department = get_object_or_404(
#             DepartmentTeams,
#             id=department_id,
#             company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#         )
#         return render(request, self.template_name, {
#             'department': department,
#             'department_id': department_id
#         })

#     def post(self, request, department_id):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             try:
#                 with transaction.atomic():
#                     step = request.POST.get('step')
#                     department = get_object_or_404(
#                         DepartmentTeams,
#                         id=department_id,
#                         company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                     )
#                     if step == 'employee':
#                         employee = Employee.objects.create(
#                             fullname=request.POST.get('fullname'),
#                             company=department.company,
#                             department_team=department,
#                             department_group_id=request.POST.get('department_group_id'),
#                             section_id=request.POST.get('section_id'),
#                             designation_id=request.POST.get('designation_id'),
#                             location_id=request.POST.get('location_id'),
#                             date_of_joining=request.POST.get('date_of_joining'),
#                             resign=request.POST.get('resign') == 'true',
#                             date_of_resignation=request.POST.get('date_of_resignation') or None,
#                             remarks=request.POST.get('remarks') or '',
#                             image=request.FILES.get('image') if 'image' in request.FILES else None
#                         )
#                         logger.debug(f"Employee created: {employee.emp_id}")
#                         return JsonResponse({'message': 'Employee created', 'employee_id': employee.emp_id})
#                     elif step == 'current_package':
#                         employee_id = request.POST.get('employee_id')
#                         employee = Employee.objects.get(emp_id=employee_id, department_team=department)
#                         current_package = CurrentPackageDetails.objects.create(
#                             employee=employee,
#                             gross_salary=request.POST.get('gross_salary') or None,
#                             vehicle_id=request.POST.get('vehicle_id') or None,
#                             fuel_limit=request.POST.get('fuel_limit') or None,
#                             mobile_allowance=request.POST.get('mobile_allowance') or None
#                         )
#                         logger.debug(f"CurrentPackageDetails created for employee: {employee_id}")
#                         return JsonResponse({'message': 'Current Package created'})
#                     elif step == 'proposed_package':
#                         employee_id = request.POST.get('employee_id')
#                         employee = Employee.objects.get(emp_id=employee_id, department_team=department)
#                         proposed_package = ProposedPackageDetails.objects.create(
#                             employee=employee,
#                             increment_percentage=request.POST.get('increment_percentage') or None,
#                             increased_fuel_amount=request.POST.get('increased_fuel_amount') or None,
#                             mobile_allowance=request.POST.get('mobile_allowance_proposed') or None,
#                             vehicle_id=request.POST.get('vehicle_proposed_id') or None
#                         )
#                         logger.debug(f"ProposedPackageDetails created for employee: {employee_id}")
#                         return JsonResponse({'message': 'Proposed Package created'})
#                     elif step == 'financial_impact':
#                         employee_id = request.POST.get('employee_id')
#                         employee = Employee.objects.get(emp_id=employee_id, department_team=department)
#                         financial_impact = FinancialImpactPerMonth.objects.create(
#                             employee=employee,
#                             emp_status_id=request.POST.get('emp_status_id') or None
#                         )
#                         logger.debug(f"FinancialImpactPerMonth created for employee: {employee_id}")
#                         return JsonResponse({'message': 'Financial Impact created'})
#                     return JsonResponse({'error': 'Invalid step'}, status=400)
#             except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
#                 logger.error(f"Error in CreateEmployeeView: {str(e)}")
#                 return JsonResponse({'error': 'Invalid data'}, status=400)
#         return JsonResponse({'error': 'Invalid request'}, status=400)



# class UpdateEmployeeView(View):
#     template_name = 'update_dept_table.html'

#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = permission_required('user.change_employee', raise_exception=True)(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, department_id, employee_id):
#         department = get_object_or_404(
#             DepartmentTeams,
#             id=department_id,
#             company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#         )
#         employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
#         return render(request, self.template_name, {
#             'department': department,
#             'department_id': department_id,
#             'employee_id': employee_id
#         })

#     def post(self, request, department_id, employee_id):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             try:
#                 department = get_object_or_404(
#                     DepartmentTeams,
#                     id=department_id,
#                     company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                 )
#                 employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
#                 step = request.POST.get('step')

#                 if step == 'employee':
#                     employee.fullname = request.POST.get('fullname')
#                     employee.department_group_id = request.POST.get('department_group_id')
#                     employee.section_id = request.POST.get('section_id')
#                     employee.designation_id = request.POST.get('designation_id')
#                     employee.location_id = request.POST.get('location_id')
#                     employee.date_of_joining = request.POST.get('date_of_joining')
#                     employee.resign = request.POST.get('resign') == 'true'
#                     employee.date_of_resignation = request.POST.get('date_of_resignation') or None
#                     employee.remarks = request.POST.get('remarks') or ''
#                     if 'image' in request.FILES:
#                         employee.image = request.FILES['image']
#                     employee.save()
#                     logger.debug(f"Employee updated: {employee_id}")
#                     return JsonResponse({'message': 'Employee updated', 'employee_id': employee_id})

#                 elif step == 'current_package':
#                     current_package, created = CurrentPackageDetails.objects.get_or_create(employee=employee)
#                     current_package.gross_salary = request.POST.get('gross_salary') or None
#                     current_package.vehicle_id = request.POST.get('vehicle_id') or None
#                     current_package.fuel_limit = request.POST.get('fuel_limit') or None
#                     current_package.mobile_allowance = request.POST.get('mobile_allowance') or None
#                     current_package.save()
#                     logger.debug(f"CurrentPackageDetails updated for employee: {employee_id}")
#                     return JsonResponse({'message': 'Current Package updated'})

#                 elif step == 'proposed_package':
#                     proposed_package, created = ProposedPackageDetails.objects.get_or_create(employee=employee)
#                     proposed_package.increment_percentage = request.POST.get('increment_percentage') or None
#                     proposed_package.increased_fuel_amount = request.POST.get('increased_fuel_amount') or None
#                     proposed_package.mobile_allowance = request.POST.get('mobile_allowance_proposed') or None
#                     proposed_package.vehicle_id = request.POST.get('vehicle_proposed_id') or None
#                     proposed_package.save()
#                     logger.debug(f"ProposedPackageDetails updated for employee: {employee_id}")
#                     return JsonResponse({'message': 'Proposed Package updated'})

#                 elif step == 'financial_impact':
#                     financial_impact, created = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
#                     financial_impact.emp_status_id = request.POST.get('emp_status_id') or None
#                     financial_impact.save()
#                     logger.debug(f"FinancialImpactPerMonth updated for employee: {employee_id}")
#                     return JsonResponse({'message': 'Financial Impact updated'})

#                 return JsonResponse({'error': 'Invalid step'}, status=400)
#             except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
#                 logger.error(f"Error in UpdateEmployeeView: {str(e)}")
#                 return JsonResponse({'error': 'Invalid data'}, status=400)
#         return JsonResponse({'error': 'Invalid request'}, status=400)




# class DeleteEmployeeView(View):
#     template_name = 'delete_employee.html'

#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = permission_required('user.delete_employee', raise_exception=True)(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, department_id, employee_id):
#         department = get_object_or_404(
#             DepartmentTeams,
#             id=department_id,
#             company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#         )
#         employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
#         return render(request, self.template_name, {
#             'department': department,
#             'department_id': department_id,
#             'employee': employee,
#             'employee_id': employee_id
#         })

#     def post(self, request, department_id, employee_id):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             try:
#                 department = get_object_or_404(
#                     DepartmentTeams,
#                     id=department_id,
#                     company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                 )
#                 employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
#                 employee.delete()
#                 logger.debug(f"Employee deleted: {employee_id}")
#                 return JsonResponse({'message': 'Employee deleted successfully'})
#             except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist):
#                 logger.error(f"Error in DeleteEmployeeView: Employee or department not found")
#                 return JsonResponse({'error': 'Invalid data'}, status=400)
#         return JsonResponse({'error': 'Invalid request'}, status=400)




# class GetDataView(View):
#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         return view

#     def get(self, request, table, id):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             try:
#                 if table == 'employee':
#                     logger.debug(f"Fetching employee with emp_id: {id}")
#                     employee = Employee.objects.filter(
#                         emp_id=id,
#                         department_team__company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                     ).first()
#                     if not employee:
#                         logger.error(f"Employee with emp_id {id} not found or not authorized")
#                         return JsonResponse({'error': f'Employee with ID {id} not found'}, status=404)
#                     current_package = CurrentPackageDetails.objects.filter(employee=employee).first() or {}
#                     proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first() or {}
#                     financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first() or {}
#                     data = {
#                         'employee': {
#                             'fullname': employee.fullname,
#                             'department_group_id': employee.department_group_id,
#                             'section_id': employee.section_id,
#                             'designation_id': employee.designation_id,
#                             'location_id': employee.location_id,
#                             'date_of_joining': employee.date_of_joining.isoformat() if employee.date_of_joining else '',
#                             'resign': employee.resign,
#                             'date_of_resignation': employee.date_of_resignation.isoformat() if employee.date_of_resignation else '',
#                             'remarks': employee.remarks or '',
#                             'image': employee.image.url if employee.image else ''
#                         },
#                         'current_package': {
#                             'gross_salary': str(current_package.gross_salary) if current_package and current_package.gross_salary else '',
#                             'vehicle_id': current_package.vehicle_id if current_package else '',
#                             'fuel_limit': str(current_package.fuel_limit) if current_package and current_package.fuel_limit else '',
#                             'mobile_allowance': str(current_package.mobile_allowance) if current_package and current_package.mobile_allowance else ''
#                         },
#                         'proposed_package': {
#                             'increment_percentage': str(proposed_package.increment_percentage) if proposed_package and proposed_package.increment_percentage else '',
#                             'increased_amount': str(proposed_package.increased_amount) if proposed_package and proposed_package.increased_amount else '',
#                             'revised_salary': str(proposed_package.revised_salary) if proposed_package and proposed_package.revised_salary else '',
#                             'increased_fuel_amount': str(proposed_package.increased_fuel_amount) if proposed_package and proposed_package.increased_fuel_amount else '',
#                             'revised_fuel_allowance': str(proposed_package.revised_fuel_allowance) if proposed_package and proposed_package.revised_fuel_allowance else '',
#                             'mobile_allowance': str(proposed_package.mobile_allowance) if proposed_package and proposed_package.mobile_allowance else '',
#                             'vehicle_id': proposed_package.vehicle_id if proposed_package else ''
#                         },
#                         'financial_impact': {
#                             'emp_status_id': str(financial_impact.emp_status_id) if financial_impact and financial_impact.emp_status_id else '',
#                             'serving_years': str(financial_impact.serving_years) if financial_impact and financial_impact.serving_years else '',
#                             'salary': str(financial_impact.salary) if financial_impact and financial_impact.salary else '',
#                             'gratuity': str(financial_impact.gratuity) if financial_impact and financial_impact.gratuity else '',
#                             'bonus': str(financial_impact.bonus) if financial_impact and financial_impact.bonus else '',
#                             'leave_encashment': str(financial_impact.leave_encashment) if financial_impact and financial_impact.leave_encashment else '',
#                             'mobile_allowance': str(financial_impact.mobile_allowance) if financial_impact and financial_impact.mobile_allowance else '',
#                             'fuel': str(financial_impact.fuel) if financial_impact and financial_impact.fuel else '',
#                             'total': str(financial_impact.total) if financial_impact and financial_impact.total else ''
#                         }
#                     }
#                     return JsonResponse({'data': data})
#                 return JsonResponse({'error': 'Invalid table'}, status=400)
#             except (Employee.DoesNotExist, ValueError) as e:
#                 logger.error(f"Error fetching employee {id}: {str(e)}")
#                 return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)
#         return JsonResponse({'error': 'Invalid request'}, status=400)



'''
Refracted code as per new model 
'''

# ✅ DepartmentTableView - updated to reflect model changes
# class DepartmentTableView(View):
#     template_name = 'dept_table_list.html'

#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, department_id):
#         department = DepartmentTeams.objects.filter(
#             id=department_id,
#             company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#         ).first()
#         if not department:
#             return render(request, 'error.html', {'error': 'Invalid department'}, status=400)

#         company_data = get_companies_and_department_teams(request.user)
#         employees = Employee.objects.filter(department_team=department).select_related(
#             'company', 'department_team', 'department_group', 'section', 'designation', 'location'
#         ).prefetch_related(
#             'currentpackagedetails', 'proposedpackagedetails', 'financialimpactpermonth', 'drafts'
#         )

#         employee_data = []
#         draft_data = {}

#         for emp in employees:
#             emp_draft = emp.drafts.first()
#             is_draft = bool(emp_draft)

#             data = {
#                 'emp_id': emp.emp_id,
#                 'fullname': emp_draft.fullname if is_draft and emp_draft.edited_fields.get('fullname') else emp.fullname,
#                 'company': emp.company.name,
#                 'department_team': emp.department_team,
#                 'department_group': emp_draft.department_group if is_draft and emp_draft.edited_fields.get('department_group_id') else emp.department_group,
#                 'section': emp_draft.section if is_draft and emp_draft.edited_fields.get('section_id') else emp.section,
#                 'designation': emp_draft.designation if is_draft and emp_draft.edited_fields.get('designation_id') else emp.designation,
#                 'location': emp_draft.location if is_draft and emp_draft.edited_fields.get('location_id') else emp.location,
#                 'date_of_joining': emp_draft.date_of_joining if is_draft and emp_draft.edited_fields.get('date_of_joining') else emp.date_of_joining,
#                 'resign': emp_draft.resign if is_draft and emp_draft.edited_fields.get('resign') else emp.resign,
#                 'date_of_resignation': emp_draft.date_of_resignation if is_draft and emp_draft.edited_fields.get('date_of_resignation') else emp.date_of_resignation,
#                 'remarks': emp_draft.remarks if is_draft and emp_draft.edited_fields.get('remarks') else emp.remarks,
#                 'is_draft': is_draft,
#                 'currentpackagedetails': None,
#                 'proposedpackagedetails': None,
#                 'financialimpactpermonth': None,
#             }

#             draft_data[emp.emp_id] = {'employee': {}, 'current_package': {}, 'proposed_package': {}, 'financial_impact': {}}

#             # ✅ Handle current package
#             current_draft = emp_draft.current_package_drafts.first() if is_draft else None
#             # current_package = emp.currentpackagedetails or current_draft

#             # Handle current package
#             current_package = getattr(emp, 'currentpackagedetails', None) or current_draft
#             if current_package:
#                 data['currentpackagedetails'] = {
#                     'gross_salary': current_package.gross_salary,
#                     'vehicle': current_package.vehicle,
#                     'fuel_limit': current_package.fuel_limit,
#                     'fuel_litre': current_package.fuel_litre,
#                     'vehicle_allowance': current_package.vehicle_allowance,
#                     'mobile_provided': current_package.mobile_provided,
#                     'total': current_package.total,
#                 }

#             # ✅ Handle proposed package
#             proposed_draft = emp_draft.proposed_package_drafts.first() if is_draft else None
#             # proposed_package = emp.proposedpackagedetails or proposed_draft

#             # Handle proposed package   
#             proposed_package = getattr(emp, 'proposedpackagedetails', None) or proposed_draft
#             if proposed_package:
#                 data['proposedpackagedetails'] = {
#                     'increment_percentage': proposed_package.increment_percentage,
#                     'increased_amount': proposed_package.increased_amount,
#                     'revised_salary': proposed_package.revised_salary,
#                     'increased_fuel_amount': proposed_package.increased_fuel_amount,
#                     'revised_fuel_allowance': proposed_package.revised_fuel_allowance,
#                     'fuel_litre': proposed_package.fuel_litre,
#                     'vehicle_allowance': proposed_package.vehicle_allowance,
#                     'mobile_provided': proposed_package.mobile_provided,
#                     'total': proposed_package.total,
#                     'approved': proposed_package.approved,
#                     'vehicle': proposed_package.vehicle,
#                 }

#             # ✅ Handle financial impact
#             financial_draft = emp_draft.financial_impact_drafts.first() if is_draft else None
#             financial_package, _ = FinancialImpactPerMonth.objects.get_or_create(employee=emp)
#             # financial_package = financial_draft or financial_package

#             financial_package = getattr(emp, 'financialimpactpermonth', None) or financial_draft
#             if financial_package:
#                 data['financialimpactpermonth'] = {
#                     'emp_status': financial_package.emp_status,
#                     'serving_years': financial_package.serving_years,
#                     'salary': financial_package.salary,
#                     'gratuity': financial_package.gratuity,
#                     'bonus': financial_package.bonus,
#                     'leave_encashment': financial_package.leave_encashment,
#                     'fuel': financial_package.fuel,
#                     'vehicle': financial_package.vehicle,
#                     'total': financial_package.total,
#                 }

#             employee_data.append(data)

#         return render(request, self.template_name, {
#             'department': department,
#             'employees': employee_data,
#             'department_id': department_id,
#             'company_data': company_data,
#             'draft_data': draft_data
#         })


'''
update code
'''

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
        employees = Employee.objects.filter(department_team=department).select_related(
            'company', 'department_team', 'department_group', 'section', 'designation', 'location'
        ).prefetch_related(
            'currentpackagedetails', 'proposedpackagedetails', 'financialimpactpermonth', 'drafts'
        )

        employee_data = []
        draft_data = {}

        for emp in employees:
            emp_draft = emp.drafts.first()
            is_draft = bool(emp_draft)

            data = {
                'emp_id': emp.emp_id,
                'fullname': emp_draft.fullname if is_draft and emp_draft.edited_fields.get('fullname') else emp.fullname,
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

            draft_data[emp.emp_id] = {'employee': {}, 'current_package': {}, 'proposed_package': {}, 'financial_impact': {}}

            # ✅ Handle current package
            current_draft = emp_draft.current_package_drafts.first() if is_draft else None
            current_package = current_draft or getattr(emp, 'currentpackagedetails', None)
            if current_package:
                data['currentpackagedetails'] = {
                    'gross_salary': current_package.gross_salary,
                    'vehicle': current_package.vehicle,
                    'fuel_limit': current_package.fuel_limit,
                    'fuel_litre': current_package.fuel_litre,
                    'vehicle_allowance': current_package.vehicle_allowance,
                    'mobile_provided': current_package.mobile_provided,
                    'total': current_package.total,
                }

            # ✅ Handle proposed package
            proposed_draft = emp_draft.proposed_package_drafts.first() if is_draft else None
            proposed_package = proposed_draft or getattr(emp, 'proposedpackagedetails', None)
            if proposed_package:
                data['proposedpackagedetails'] = {
                    'increment_percentage': proposed_package.increment_percentage,
                    'increased_amount': proposed_package.increased_amount,
                    'revised_salary': proposed_package.revised_salary,
                    'increased_fuel_amount': proposed_package.increased_fuel_amount,
                    'revised_fuel_allowance': proposed_package.revised_fuel_allowance,
                    'fuel_litre': proposed_package.fuel_litre,
                    'vehicle_allowance': proposed_package.vehicle_allowance,
                    'mobile_provided': proposed_package.mobile_provided,
                    'total': proposed_package.total,
                    'approved': proposed_package.approved,
                    'vehicle': proposed_package.vehicle,
                }

            # ✅ Handle financial impact (Prioritize draft)
            financial_draft = emp_draft.financial_impact_drafts.first() if is_draft else None
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
            'draft_data': draft_data
        })




from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie


# @method_decorator(login_required, name='dispatch')
# @method_decorator(cache_control(no_cache=True, must_revalidate=True, no_store=True), name='dispatch')
# @method_decorator(ensure_csrf_cookie, name='dispatch')
# class GetEmployeeDataView(View):
#     def get(self, request, employee_id):
#         try:
#             # Optimize queries using select_related
#             employee = Employee.objects.select_related(
#                 'department_group', 'section', 'designation', 'location'
#             ).get(emp_id=employee_id)

#             current_package = CurrentPackageDetails.objects.select_related('vehicle').filter(employee=employee).first()
#             proposed_package = ProposedPackageDetails.objects.select_related('vehicle').filter(employee=employee).first()
#             financial_impact = FinancialImpactPerMonth.objects.select_related('emp_status').filter(employee=employee).first()

#             # Helper to format date
#             def fmt_date(date):
#                 return date.strftime('%Y-%m-%d') if date else ''

#             # Helper to safely convert decimal/float fields
#             def fmt_float(value):
#                 return float(value) if value is not None else ''

#             data = {
#                 'employee': {
#                     'fullname': employee.fullname,
#                     'department_group_id': getattr(employee.department_group, 'id', None),
#                     'section_id': getattr(employee.section, 'id', None),
#                     'designation_id': getattr(employee.designation, 'id', None),
#                     'location_id': getattr(employee.location, 'id', None),
#                     'date_of_joining': fmt_date(employee.date_of_joining),
#                     'resign': employee.resign,
#                     'date_of_resignation': fmt_date(employee.date_of_resignation),
#                     'remarks': employee.remarks or ''
#                 },
#                 'current_package': {
#                     'gross_salary': fmt_float(getattr(current_package, 'gross_salary', None)),
#                     'vehicle_id': getattr(getattr(current_package, 'vehicle', None), 'id', ''),
#                     'fuel_limit': fmt_float(getattr(current_package, 'fuel_limit', None)),
#                     'mobile_allowance': fmt_float(getattr(current_package, 'mobile_allowance', None))
#                 },
#                 'proposed_package': {
#                     'increment_percentage': fmt_float(getattr(proposed_package, 'increment_percentage', None)),
#                     'increased_amount': fmt_float(getattr(proposed_package, 'increased_amount', None)),
#                     'revised_salary': fmt_float(getattr(proposed_package, 'revised_salary', None)),
#                     'increased_fuel_amount': fmt_float(getattr(proposed_package, 'increased_fuel_amount', None)),
#                     'revised_fuel_allowance': fmt_float(getattr(proposed_package, 'revised_fuel_allowance', None)),
#                     'mobile_allowance': fmt_float(getattr(proposed_package, 'mobile_allowance', None)),
#                     'vehicle_id': getattr(getattr(proposed_package, 'vehicle', None), 'id', '')
#                 },
#                 'financial_impact': {
#                     'emp_status_id': getattr(getattr(financial_impact, 'emp_status', None), 'id', ''),
#                     'serving_years': getattr(financial_impact, 'serving_years', ''),
#                     'salary': fmt_float(getattr(financial_impact, 'salary', None)),
#                     'gratuity': fmt_float(getattr(financial_impact, 'gratuity', None)),
#                     'bonus': fmt_float(getattr(financial_impact, 'bonus', None)),
#                     'leave_encashment': fmt_float(getattr(financial_impact, 'leave_encashment', None)),
#                     'mobile_allowance': fmt_float(getattr(financial_impact, 'mobile_allowance', None)),
#                     'fuel': fmt_float(getattr(financial_impact, 'fuel', None)),
#                     'total': fmt_float(getattr(financial_impact, 'total', None)),
#                 }
#             }

#             return JsonResponse({'data': data})

#         except Employee.DoesNotExist:
#             return JsonResponse({'error': 'Employee not found'}, status=404)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)


'''
Updated code as per change in model
'''
# @method_decorator(login_required, name='dispatch')
# @method_decorator(cache_control(no_cache=True, must_revalidate=True, no_store=True), name='dispatch')
# @method_decorator(ensure_csrf_cookie, name='dispatch')
# class GetEmployeeDataView(View):
#     def get(self, request, employee_id):
#         try:
#             # Optimize queries using select_related and check authorization
#             employee = Employee.objects.select_related(
#                 'department_group', 'section', 'designation', 'location', 'department_team__company'
#             ).filter(
#                 emp_id=employee_id,
#                 department_team__company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#             ).first()

#             if not employee:
#                 return JsonResponse({'error': 'Employee not found or not authorized'}, status=404)

#             current_package = CurrentPackageDetails.objects.select_related('vehicle').filter(employee=employee).first()
#             proposed_package = ProposedPackageDetails.objects.select_related('vehicle').filter(employee=employee).first()
#             financial_impact = FinancialImpactPerMonth.objects.select_related('emp_status').filter(employee=employee).first()

#             # Helper to format date
#             def fmt_date(date):
#                 return date.strftime('%Y-%m-%d') if date else ''

#             # Helper to safely convert decimal/float fields to strings
#             def fmt_float(value):
#                 return str(value) if value is not None else ''

#             data = {
#                 'employee': {
#                     'fullname': employee.fullname,
#                     'department_group_id': getattr(employee.department_group, 'id', None),
#                     'section_id': getattr(employee.section, 'id', None),
#                     'designation_id': getattr(employee.designation, 'id', None),
#                     'location_id': getattr(employee.location, 'id', None),
#                     'date_of_joining': fmt_date(employee.date_of_joining),
#                     'resign': employee.resign,
#                     'date_of_resignation': fmt_date(employee.date_of_resignation),
#                     'eligible_for_increment': employee.eligible_for_increment,
#                     'remarks': employee.remarks or '',
#                     'image': employee.image.url if employee.image else ''
#                 },
#                 'current_package': {
#                     'gross_salary': fmt_float(getattr(current_package, 'gross_salary', None)),
#                     'vehicle_id': getattr(getattr(current_package, 'vehicle', None), 'id', ''),
#                     'fuel_limit': fmt_float(getattr(current_package, 'fuel_limit', None)),
#                     'mobile_provided': getattr(current_package, 'mobile_provided', False),
#                     'fuel_litre': fmt_float(getattr(current_package, 'fuel_litre', None)),
#                     'total': fmt_float(getattr(current_package, 'total', None))
#                 },
#                 'proposed_package': {
#                     'increment_percentage': fmt_float(getattr(proposed_package, 'increment_percentage', None)),
#                     'increased_fuel_amount': fmt_float(getattr(proposed_package, 'increased_fuel_amount', None)),
#                     'revised_salary': fmt_float(getattr(proposed_package, 'revised_salary', None)),
#                     'mobile_provided': getattr(proposed_package, 'mobile_provided', False),
#                     'vehicle_id': getattr(getattr(proposed_package, 'vehicle', None), 'id', ''),
#                     'fuel_litre': fmt_float(getattr(proposed_package, 'fuel_litre', None)),
#                     'vehicle_allowance': fmt_float(getattr(proposed_package, 'vehicle_allowance', None)),
#                     'approved': getattr(proposed_package, 'approved', False),
#                     'total': fmt_float(getattr(proposed_package, 'total', None))
#                 },
#                 'financial_impact': {
#                     'emp_status_id': getattr(getattr(financial_impact, 'emp_status', None), 'id', ''),
#                     'serving_years': fmt_float(getattr(financial_impact, 'serving_years', None)),
#                     'salary': fmt_float(getattr(financial_impact, 'salary', None)),
#                     'gratuity': fmt_float(getattr(financial_impact, 'gratuity', None))
#                 }
#             }

#             return JsonResponse({'data': data})

#         except Employee.DoesNotExist:
#             return JsonResponse({'error': 'Employee not found'}, status=404)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)



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
                    'vehicle_id': getattr(getattr(use_current, 'vehicle', None), 'id', ''),
                    'fuel_limit': fmt_float(getattr(use_current, 'fuel_limit', None)),
                    'mobile_allowance': fmt_float(getattr(use_current, 'mobile_allowance', None)),
                },
                'proposed_package': {
                    'increment_percentage': fmt_float(getattr(use_proposed, 'increment_percentage', None)),
                    'increased_amount': fmt_float(getattr(use_proposed, 'increased_amount', None)),
                    'increased_fuel_amount': fmt_float(getattr(use_proposed, 'increased_fuel_amount', None)),
                    'mobile_allowance': fmt_float(getattr(use_proposed, 'mobile_allowance', None)),
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




# class CreateEmployeeView(View):
#     template_name = 'create_dept_table.html'

#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = permission_required('user.add_employee', raise_exception=True)(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, department_id):
#         department = get_object_or_404(
#             DepartmentTeams,
#             id=department_id,
#             company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#         )
#         return render(request, self.template_name, {
#             'department': department,
#             'department_id': department_id
#         })

#     def post(self, request, department_id):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             try:
#                 with transaction.atomic():
#                     step = request.POST.get('step')

#                     # Validate department
#                     department = get_object_or_404(
#                         DepartmentTeams,
#                         id=department_id,
#                         company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                     )

#                     # STEP 1: Create Employee
#                     if step == 'employee':
#                         employee = Employee.objects.create(
#                             fullname=request.POST.get('fullname'),
#                             company=department.company,
#                             department_team=department,
#                             department_group_id=request.POST.get('department_group_id') or None,
#                             section_id=request.POST.get('section_id') or None,
#                             designation_id=request.POST.get('designation_id') or None,
#                             location_id=request.POST.get('location_id') or None,
#                             date_of_joining=request.POST.get('date_of_joining') or None,
#                             resign=request.POST.get('resign') == 'true',
#                             date_of_resignation=request.POST.get('date_of_resignation') or None,
#                             remarks=request.POST.get('remarks') or '',
#                             image=request.FILES.get('image') if 'image' in request.FILES else None
#                         )
#                         logger.debug(f"Employee created: {employee.emp_id}")
#                         return JsonResponse({'message': 'Employee created', 'employee_id': employee.emp_id})

#                     # STEP 2: Create Current Package
#                     elif step == 'current_package':
#                         employee_id = request.POST.get('employee_id')
#                         employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
#                         CurrentPackageDetails.objects.create(
#                             employee=employee,
#                             gross_salary=request.POST.get('gross_salary') or None,
#                             vehicle_id=request.POST.get('vehicle_id') or None,
#                             fuel_limit=request.POST.get('fuel_limit') or None,
#                             mobile_allowance=request.POST.get('mobile_allowance') or None
#                         )
#                         logger.debug(f"CurrentPackageDetails created for employee: {employee_id}")
#                         return JsonResponse({'message': 'Current Package created'})

#                     # STEP 3: Create Proposed Package
#                     elif step == 'proposed_package':
#                         employee_id = request.POST.get('employee_id')
#                         employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
#                         ProposedPackageDetails.objects.create(
#                             employee=employee,
#                             increment_percentage=request.POST.get('increment_percentage') or None,
#                             increased_fuel_amount=request.POST.get('increased_fuel_amount') or None,
#                             mobile_allowance=request.POST.get('mobile_allowance_proposed') or None,
#                             vehicle_id=request.POST.get('vehicle_proposed_id') or None
#                         )
#                         logger.debug(f"ProposedPackageDetails created for employee: {employee_id}")
#                         return JsonResponse({'message': 'Proposed Package created'})

#                     # STEP 4: Create Financial Impact
#                     elif step == 'financial_impact':
#                         employee_id = request.POST.get('employee_id')
#                         employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
#                         FinancialImpactPerMonth.objects.create(
#                             employee=employee,
#                             emp_status_id=request.POST.get('emp_status_id') or None,
#                             serving_years=request.POST.get('serving_years') or None,
#                             salary=request.POST.get('salary') or None,
#                             gratuity=request.POST.get('gratuity') or None
#                         )
#                         logger.debug(f"FinancialImpactPerMonth created for employee: {employee_id}")
#                         return JsonResponse({'message': 'Financial Impact created'})

#                     return JsonResponse({'error': 'Invalid step'}, status=400)

#             except Exception as e:
#                 logger.error(f"Error in CreateEmployeeView: {str(e)}")
#                 return JsonResponse({'error': 'Invalid data'}, status=400)

#         return JsonResponse({'error': 'Invalid request'}, status=400)


'''
Updated Code as per change in model
'''
import logging

logger = logging.getLogger(__name__)

class CreateEmployeeView(View):
    template_name = 'create_dept_table.html'

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = permission_required('user.add_employee', raise_exception=True)(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, department_id):
        department = get_object_or_404(
            DepartmentTeams,
            id=department_id,
            company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
        )
        return render(request, self.template_name, {
            'department': department,
            'department_id': department_id
        })

    def post(self, request, department_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                with transaction.atomic():
                    step = request.POST.get('step')

                    # Validate department
                    department = get_object_or_404(
                        DepartmentTeams,
                        id=department_id,
                        company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                    )

                    # STEP 1: Create Employee
                    if step == 'employee':
                        employee = Employee.objects.create(
                            emp_id=request.POST.get('emp_id'),
                            fullname=request.POST.get('fullname'),
                            company=department.company,
                            department_team=department,
                            department_group_id=request.POST.get('department_group_id') or None,
                            section_id=request.POST.get('section_id') or None,
                            designation_id=request.POST.get('designation_id') or None,
                            location_id=request.POST.get('location_id') or None,
                            date_of_joining=request.POST.get('date_of_joining') or None,
                            resign=request.POST.get('resign') == 'true',
                            date_of_resignation=request.POST.get('date_of_resignation') or None,
                            remarks=request.POST.get('remarks') or '',
                            image=request.FILES.get('image') if 'image' in request.FILES else None,
                            eligible_for_increment=request.POST.get('eligible_for_increment') == 'true'
                        )
                        logger.debug(f"Employee created: {employee.emp_id}")
                        return JsonResponse({'message': 'Employee created', 'employee_id': employee.emp_id})

                    # STEP 2: Create Current Package
                    elif step == 'current_package':
                        employee_id = request.POST.get('employee_id')
                        employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
                        CurrentPackageDetails.objects.create(
                            employee=employee,
                            gross_salary=request.POST.get('gross_salary') or None,
                            vehicle_id=request.POST.get('vehicle_id') or None,
                            fuel_limit=request.POST.get('fuel_limit') or None,
                            mobile_provided=request.POST.get('mobile_provided') == 'true',
                            fuel_litre=request.POST.get('fuel_litre') or None
                        )
                        logger.debug(f"CurrentPackageDetails created for employee: {employee_id}")
                        return JsonResponse({'message': 'Current Package created'})

                    # STEP 3: Create Proposed Package
                    elif step == 'proposed_package':
                        employee_id = request.POST.get('employee_id')
                        employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
                        ProposedPackageDetails.objects.create(
                            employee=employee,
                            increment_percentage=request.POST.get('increment_percentage') or None,
                            increased_fuel_amount=request.POST.get('increased_fuel_amount') or None,
                            mobile_provided=request.POST.get('mobile_provided_proposed') == 'true',
                            vehicle_id=request.POST.get('vehicle_proposed_id') or None,
                            fuel_litre=request.POST.get('fuel_litre') or None,
                            vehicle_allowance=request.POST.get('vehicle_allowance') or None,
                            approved=request.POST.get('approved') == 'true'
                        )
                        logger.debug(f"ProposedPackageDetails created for employee: {employee_id}")
                        return JsonResponse({'message': 'Proposed Package created'})

                    # STEP 4: Create Financial Impact
                    elif step == 'financial_impact':
                        employee_id = request.POST.get('employee_id')
                        employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
                        FinancialImpactPerMonth.objects.create(
                            employee=employee,
                            emp_status_id=request.POST.get('emp_status_id') or None,
                            serving_years=request.POST.get('serving_years') or None,
                            salary=request.POST.get('salary') or None,
                            gratuity=request.POST.get('gratuity') or None
                        )
                        logger.debug(f"FinancialImpactPerMonth created for employee: {employee_id}")
                        return JsonResponse({'message': 'Financial Impact created'})

                    return JsonResponse({'error': 'Invalid step'}, status=400)

            except Exception as e:
                logger.error(f"Error in CreateEmployeeView: {str(e)}")
                return JsonResponse({'error': 'Invalid data'}, status=400)

        return JsonResponse({'error': 'Invalid request'}, status=400)








# class UpdateEmployeeView(View):
#     template_name = 'update_dept_table.html'

#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = permission_required('user.change_employee', raise_exception=True)(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, department_id, employee_id):
#         department = get_object_or_404(
#             DepartmentTeams,
#             id=department_id,
#             company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#         )
#         employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)

#         # Get related records if exist
#         current_package = CurrentPackageDetails.objects.filter(employee=employee).first()
#         proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first()
#         financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first()

#         return render(request, self.template_name, {
#             'department': department,
#             'department_id': department_id,
#             'employee_id': employee_id,
#             'employee': employee,
#             'current_package': current_package,
#             'proposed_package': proposed_package,
#             'financial_impact': financial_impact,
#         })

#     def post(self, request, department_id, employee_id):
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             try:
#                 department = get_object_or_404(
#                     DepartmentTeams,
#                     id=department_id,
#                     company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                 )
#                 employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
#                 step = request.POST.get('step')

#                 # --- Update Employee Info ---
#                 if step == 'employee':
#                     employee.fullname = request.POST.get('fullname') or employee.fullname
#                     employee.department_group_id = request.POST.get('department_group_id') or None
#                     employee.section_id = request.POST.get('section_id') or None
#                     employee.designation_id = request.POST.get('designation_id') or None
#                     employee.location_id = request.POST.get('location_id') or None
#                     employee.date_of_joining = request.POST.get('date_of_joining') or None
#                     employee.resign = request.POST.get('resign') == 'true'
#                     employee.date_of_resignation = request.POST.get('date_of_resignation') or None
#                     employee.remarks = request.POST.get('remarks') or ''
#                     if 'image' in request.FILES:
#                         employee.image = request.FILES['image']
#                     employee.save()
#                     logger.debug(f"Employee updated: {employee_id}")
#                     return JsonResponse({'message': 'Employee updated', 'employee_id': employee_id})

#                 # --- Update Current Package ---
#                 elif step == 'current_package':
#                     current_package, _ = CurrentPackageDetails.objects.get_or_create(employee=employee)
#                     current_package.gross_salary = request.POST.get('gross_salary') or None
#                     current_package.vehicle_id = request.POST.get('vehicle_id') or None
#                     current_package.fuel_limit = request.POST.get('fuel_limit') or None
#                     current_package.mobile_allowance = request.POST.get('mobile_allowance') or None
#                     current_package.save()
#                     logger.debug(f"CurrentPackageDetails updated for employee: {employee_id}")
#                     return JsonResponse({'message': 'Current Package updated'})

#                 # --- Update Proposed Package ---
#                 elif step == 'proposed_package':
#                     proposed_package, _ = ProposedPackageDetails.objects.get_or_create(employee=employee)
#                     proposed_package.increment_percentage = request.POST.get('increment_percentage') or None
#                     proposed_package.increased_fuel_amount = request.POST.get('increased_fuel_amount') or None
#                     proposed_package.mobile_allowance = request.POST.get('mobile_allowance_proposed') or None
#                     proposed_package.vehicle_id = request.POST.get('vehicle_proposed_id') or None
#                     proposed_package.save()
#                     logger.debug(f"ProposedPackageDetails updated for employee: {employee_id}")
#                     return JsonResponse({'message': 'Proposed Package updated'})

#                 # --- Update Financial Impact ---
#                 elif step == 'financial_impact':
#                     financial_impact, _ = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
#                     financial_impact.emp_status_id = request.POST.get('emp_status_id') or None
#                     financial_impact.serving_years = request.POST.get('serving_years') or None
#                     financial_impact.salary = request.POST.get('salary') or None
#                     financial_impact.gratuity = request.POST.get('gratuity') or None
#                     financial_impact.save()
#                     logger.debug(f"FinancialImpactPerMonth updated for employee: {employee_id}")
#                     return JsonResponse({'message': 'Financial Impact updated'})

#                 return JsonResponse({'error': 'Invalid step'}, status=400)

#             except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
#                 logger.error(f"Error in UpdateEmployeeView: {str(e)}")
#                 return JsonResponse({'error': 'Invalid data'}, status=400)

#         return JsonResponse({'error': 'Invalid request'}, status=400)


'''
Updated code as per change in model
'''


class UpdateEmployeeView(View):
    template_name = 'update_dept_table.html'

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = permission_required('user.change_employee', raise_exception=True)(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, department_id, employee_id):
        department = get_object_or_404(
            DepartmentTeams,
            id=department_id,
            company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
        )
        employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)

        # Get related records if exist
        current_package = CurrentPackageDetails.objects.filter(employee=employee).first()
        proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first()
        financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first()

        return render(request, self.template_name, {
            'department': department,
            'department_id': department_id,
            'employee_id': employee_id,
            'employee': employee,
            'current_package': current_package,
            'proposed_package': proposed_package,
            'financial_impact': financial_impact,
        })

    def post(self, request, department_id, employee_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                department = get_object_or_404(
                    DepartmentTeams,
                    id=department_id,
                    company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                )
                employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)
                step = request.POST.get('step')

                # --- Update Employee Info ---
                if step == 'employee':
                    employee.fullname = request.POST.get('fullname') or employee.fullname
                    employee.department_group_id = request.POST.get('department_group_id') or None
                    employee.section_id = request.POST.get('section_id') or None
                    employee.designation_id = request.POST.get('designation_id') or None
                    employee.location_id = request.POST.get('location_id') or None
                    employee.date_of_joining = request.POST.get('date_of_joining') or None
                    employee.resign = request.POST.get('resign') == 'true'
                    employee.date_of_resignation = request.POST.get('date_of_resignation') or None
                    employee.remarks = request.POST.get('remarks') or ''
                    employee.eligible_for_increment = request.POST.get('eligible_for_increment') == 'true'
                    if 'image' in request.FILES:
                        employee.image = request.FILES['image']
                    employee.save()
                    logger.debug(f"Employee updated: {employee_id}")
                    return JsonResponse({'message': 'Employee updated', 'employee_id': employee_id})

                # --- Update Current Package ---
                elif step == 'current_package':
                    current_package, _ = CurrentPackageDetails.objects.get_or_create(employee=employee)
                    current_package.gross_salary = request.POST.get('gross_salary') or None
                    current_package.vehicle_id = request.POST.get('vehicle_id') or None
                    current_package.fuel_limit = request.POST.get('fuel_limit') or None
                    current_package.mobile_provided = request.POST.get('mobile_provided') == 'true'
                    current_package.fuel_litre = request.POST.get('fuel_litre') or None
                    current_package.save()
                    logger.debug(f"CurrentPackageDetails updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Current Package updated'})

                # --- Update Proposed Package ---
                elif step == 'proposed_package':
                    proposed_package, _ = ProposedPackageDetails.objects.get_or_create(employee=employee)
                    proposed_package.increment_percentage = request.POST.get('increment_percentage') or None
                    proposed_package.increased_fuel_amount = request.POST.get('increased_fuel_amount') or None
                    proposed_package.mobile_provided = request.POST.get('mobile_provided_proposed') == 'true'
                    proposed_package.vehicle_id = request.POST.get('vehicle_proposed_id') or None
                    proposed_package.fuel_litre = request.POST.get('fuel_litre') or None
                    proposed_package.vehicle_allowance = request.POST.get('vehicle_allowance') or None
                    proposed_package.approved = request.POST.get('approved') == 'true'
                    proposed_package.save()
                    logger.debug(f"ProposedPackageDetails updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Proposed Package updated'})

                # --- Update Financial Impact ---
                elif step == 'financial_impact':
                    financial_impact, _ = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
                    financial_impact.emp_status_id = request.POST.get('emp_status_id') or None
                    financial_impact.serving_years = request.POST.get('serving_years') or None
                    financial_impact.salary = request.POST.get('salary') or None
                    financial_impact.gratuity = request.POST.get('gratuity') or None
                    financial_impact.save()
                    logger.debug(f"FinancialImpactPerMonth updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Financial Impact updated'})

                return JsonResponse({'error': 'Invalid step'}, status=400)

            except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
                logger.error(f"Error in UpdateEmployeeView: {str(e)}")
                return JsonResponse({'error': 'Invalid data'}, status=400)

        return JsonResponse({'error': 'Invalid request'}, status=400)





class DeleteEmployeeView(View):
    template_name = 'delete_employee.html'

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = permission_required('user.delete_employee', raise_exception=True)(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, department_id, employee_id):
        """Render the delete confirmation page."""
        department = get_object_or_404(
            DepartmentTeams,
            id=department_id,
            company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
        )
        employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)

        context = {
            'department': department,
            'department_id': department_id,
            'employee': employee,
            'employee_id': employee_id,
        }
        return render(request, self.template_name, context)

    def post(self, request, department_id, employee_id):
        """Handle employee deletion via AJAX."""
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({'error': 'Invalid request'}, status=400)

        try:
            department = get_object_or_404(
                DepartmentTeams,
                id=department_id,
                company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
            )
            employee = get_object_or_404(Employee, emp_id=employee_id, department_team=department)

            employee.delete()
            logger.debug(f"Employee deleted: {employee_id}")
            return JsonResponse({'message': 'Employee deleted successfully'})

        except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist):
            logger.error("Error in DeleteEmployeeView: Employee or department not found")
            return JsonResponse({'error': 'Invalid data'}, status=400)


# class GetDataView(View):
#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = ensure_csrf_cookie(view)
#         return view

#     def get(self, request, table, id):
#         if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
#             return JsonResponse({'error': 'Invalid request'}, status=400)

#         try:
#             if table == 'employee':
#                 logger.debug(f"Fetching employee with emp_id: {id}")

#                 employee = Employee.objects.filter(
#                     emp_id=id,
#                     department_team__company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
#                 ).first()

#                 if not employee:
#                     logger.error(f"Employee with emp_id {id} not found or not authorized")
#                     return JsonResponse({'error': f'Employee with ID {id} not found'}, status=404)

#                 current_package = CurrentPackageDetails.objects.filter(employee=employee).first() or {}
#                 proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first() or {}
#                 financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first() or {}

#                 data = {
#                     'employee': {
#                         'fullname': employee.fullname,
#                         'department_group_id': employee.department_group_id,
#                         'section_id': employee.section_id,
#                         'designation_id': employee.designation_id,
#                         'location_id': employee.location_id,
#                         'date_of_joining': employee.date_of_joining.isoformat() if employee.date_of_joining else '',
#                         'resign': employee.resign,
#                         'date_of_resignation': employee.date_of_resignation.isoformat() if employee.date_of_resignation else '',
#                         'remarks': employee.remarks or '',
#                         'image': employee.image.url if employee.image else ''
#                     },
#                     'current_package': {
#                         'gross_salary': str(current_package.gross_salary) if current_package and current_package.gross_salary else '',
#                         'vehicle_id': current_package.vehicle_id if current_package else '',
#                         'fuel_limit': str(current_package.fuel_limit) if current_package and current_package.fuel_limit else '',
#                         'mobile_allowance': str(current_package.mobile_allowance) if current_package and current_package.mobile_allowance else ''
#                     },
#                     'proposed_package': {
#                         'increment_percentage': str(proposed_package.increment_percentage) if proposed_package and proposed_package.increment_percentage else '',
#                         'increased_amount': str(proposed_package.increased_amount) if proposed_package and proposed_package.increased_amount else '',
#                         'revised_salary': str(proposed_package.revised_salary) if proposed_package and proposed_package.revised_salary else '',
#                         'increased_fuel_amount': str(proposed_package.increased_fuel_amount) if proposed_package and proposed_package.increased_fuel_amount else '',
#                         'revised_fuel_allowance': str(proposed_package.revised_fuel_allowance) if proposed_package and proposed_package.revised_fuel_allowance else '',
#                         'mobile_allowance': str(proposed_package.mobile_allowance) if proposed_package and proposed_package.mobile_allowance else '',
#                         'vehicle_id': proposed_package.vehicle_id if proposed_package else ''
#                     },
#                     'financial_impact': {
#                         'emp_status_id': str(financial_impact.emp_status_id) if financial_impact and financial_impact.emp_status_id else '',
#                         'serving_years': str(financial_impact.serving_years) if financial_impact and financial_impact.serving_years else '',
#                         'salary': str(financial_impact.salary) if financial_impact and financial_impact.salary else '',
#                         'gratuity': str(financial_impact.gratuity) if financial_impact and financial_impact.gratuity else '',
#                         'bonus': str(financial_impact.bonus) if financial_impact and financial_impact.bonus else '',
#                         'leave_encashment': str(financial_impact.leave_encashment) if financial_impact and financial_impact.leave_encashment else '',
#                         'mobile_allowance': str(financial_impact.mobile_allowance) if financial_impact and financial_impact.mobile_allowance else '',
#                         'fuel': str(financial_impact.fuel) if financial_impact and financial_impact.fuel else '',
#                         'total': str(financial_impact.total) if financial_impact and financial_impact.total else ''
#                     }
#                 }

#                 return JsonResponse({'data': data})

#             return JsonResponse({'error': 'Invalid table'}, status=400)

#         except Exception as e:
#             logger.error(f"Error in GetDataView: {str(e)}")
#             return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)


'''
Updated code as per chnage in model
'''


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
                        'fullname': employee.fullname,
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
                        'vehicle_id': current_package.vehicle_id if current_package else '',
                        'fuel_limit': str(current_package.fuel_limit) if current_package and current_package.fuel_limit else '',
                        'mobile_provided': current_package.mobile_provided if current_package else False,
                        'fuel_litre': str(current_package.fuel_litre) if current_package and current_package.fuel_litre else ''
                    },
                    'proposed_package': {
                        'increment_percentage': str(proposed_package.increment_percentage) if proposed_package and proposed_package.increment_percentage else '',
                        'increased_fuel_amount': str(proposed_package.increased_fuel_amount) if proposed_package and proposed_package.increased_fuel_amount else '',
                        'revised_salary': str(proposed_package.revised_salary) if proposed_package and proposed_package.revised_salary else '',
                        'mobile_provided': proposed_package.mobile_provided if proposed_package else False,
                        'vehicle_id': proposed_package.vehicle_id if proposed_package else '',
                        'fuel_litre': str(proposed_package.fuel_litre) if proposed_package and proposed_package.fuel_litre else '',
                        'vehicle_allowance': str(proposed_package.vehicle_allowance) if proposed_package and proposed_package.vehicle_allowance else '',
                        'approved': proposed_package.approved if proposed_package else False
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


# class CreateFieldFormulaView(PermissionRequiredMixin, View):
#     permission_required = "user.add_fieldformula"
#     template_name = "create_field_formula.html"

#     def get(self, request):
#         form = FieldFormulaForm()
#         field_references = FieldReference.objects.all()
#         company_data = get_companies_and_department_teams(request.user)
#         return render(request, self.template_name, {
#             'form': form,
#             'field_references': field_references,
#             'company_data': company_data
#         })

#     def post(self, request):
#         form = FieldFormulaForm(request.POST)
#         field_references = FieldReference.objects.all()
#         company_data = get_companies_and_department_teams(request.user)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Field Formula created successfully!")
#             return redirect("view_field_formulas")
#         return render(request, self.template_name, {
#             'form': form,
#             'field_references': field_references,
#             'company_data': company_data
#         })



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
        form = FieldFormulaForm(user=request.user, data=request.POST)  # Pass user
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


# class SaveDraftView(View):
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
#             drafts_saved = False
#             with transaction.atomic():
#                 for employee_id, tabs in data.items():
#                     employee = Employee.objects.filter(emp_id=employee_id, department_team_id=department_id).first()
#                     if not employee:
#                         logger.error(f"Employee {employee_id} not found for department {department_id}")
#                         return JsonResponse({'error': f'Employee {employee_id} not found'}, status=404)

#                     has_changes = False
#                     employee_draft_edited = {}
#                     current_package_edited = {}
#                     proposed_package_edited = {}
#                     financial_impact_edited = {}

#                     for tab, fields in tabs.items():
#                         if tab == 'employee':
#                             for field, value in fields.items():
#                                 if field in ['fullname', 'department_group_id', 'section_id', 'designation_id', 'location_id', 'date_of_joining', 'resign', 'date_of_resignation', 'remarks']:
#                                     current_value = getattr(employee, field, None)
#                                     if field in ['department_group_id', 'section_id', 'designation_id', 'location_id']:
#                                         current_value = getattr(getattr(employee, field, None), 'id', None)
#                                     elif field == 'resign':
#                                         current_value = str(current_value).lower()
#                                     if str(value) != str(current_value):
#                                         has_changes = True
#                                         employee_draft_edited[field] = True
#                         elif tab == 'current_package':
#                             for field, value in fields.items():
#                                 if field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'mobile_allowance']:
#                                     current_package = CurrentPackageDetails.objects.filter(employee=employee).first()
#                                     current_value = getattr(current_package, field, None) if current_package else None
#                                     if field == 'vehicle_id':
#                                         current_value = current_value.id if current_value else None
#                                     if str(value) != str(current_value):
#                                         has_changes = True
#                                         current_package_edited[field] = True
#                         elif tab == 'proposed_package':
#                             for field, value in fields.items():
#                                 if field in ['increment_percentage', 'increased_fuel_amount', 'mobile_allowance_proposed', 'vehicle_proposed_id']:
#                                     proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first()
#                                     field_key = 'mobile_allowance' if field == 'mobile_allowance_proposed' else ('vehicle_id' if field == 'vehicle_proposed_id' else field)
#                                     current_value = getattr(proposed_package, field_key, None) if proposed_package else None
#                                     if field in ['vehicle_proposed_id']:
#                                         current_value = current_value.id if current_value else None
#                                     if str(value) != str(current_value):
#                                         has_changes = True
#                                         proposed_package_edited[field_key] = True
#                         elif tab == 'financial_impact':
#                             for field, value in fields.items():
#                                 if field == 'emp_status_id':
#                                     financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first()
#                                     current_value = getattr(financial_impact, 'emp_status_id', None) if financial_impact else None
#                                     if str(value) != str(current_value):
#                                         has_changes = True
#                                         financial_impact_edited[field] = True

#                     if not has_changes:
#                         continue

#                     employee_draft = EmployeeDraft.objects.filter(employee=employee).first()
#                     if employee_draft_edited or current_package_edited or proposed_package_edited or financial_impact_edited:
#                         if not employee_draft:
#                             employee_draft = EmployeeDraft(employee=employee, company=employee.company, department_team=employee.department_team)
#                         for field, value in tabs.get('employee', {}).items():
#                             if field in ['fullname', 'department_group_id', 'section_id', 'designation_id', 'location_id', 'date_of_joining', 'resign', 'date_of_resignation', 'remarks'] and employee_draft_edited.get(field):
#                                 try:
#                                     if field == 'department_group_id':
#                                         employee_draft.department_group_id = int(value) if value else None
#                                     elif field == 'section_id':
#                                         employee_draft.section_id = int(value) if value else None
#                                     elif field == 'designation_id':
#                                         employee_draft.designation_id = int(value) if value else None
#                                         if employee_draft.designation_id:
#                                             Designation.objects.get(id=employee_draft.designation_id)  # Validate designation_id
#                                     elif field == 'location_id':
#                                         employee_draft.location_id = int(value) if value else None
#                                     elif field == 'resign':
#                                         employee_draft.resign = value == 'true'
#                                     elif field == 'date_of_joining' or field == 'date_of_resignation':
#                                         employee_draft.__setattr__(field, value or None)
#                                     elif field == 'fullname' or field == 'remarks':
#                                         employee_draft.__setattr__(field, value or None)
#                                 except (ValueError, Designation.DoesNotExist) as e:
#                                     logger.error(f"Invalid designation_id {value} for employee {employee_id}: {str(e)}")
#                                     return JsonResponse({'error': f'Invalid designation ID: {value}'}, status=400)
#                         employee_draft.edited_fields = employee_draft_edited
#                         if employee_draft_edited:
#                             employee_draft.save()
#                             drafts_saved = True

#                         if current_package_edited:
#                             draft, created = CurrentPackageDetailsDraft.objects.get_or_create(employee_draft=employee_draft)
#                             for field, value in tabs.get('current_package', {}).items():
#                                 if field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'mobile_allowance'] and current_package_edited.get(field):
#                                     try:
#                                         if field == 'vehicle_id':
#                                             draft.vehicle_id = int(value) if value else None
#                                         elif field in ['gross_salary', 'fuel_limit', 'mobile_allowance']:
#                                             draft.__setattr__(field, Decimal(value) if value else Decimal('0'))
#                                     except ValueError as e:
#                                         logger.error(f"Invalid value for {field} in current_package for employee {employee_id}: {str(e)}")
#                                         return JsonResponse({'error': f'Invalid value for {field}: {value}'}, status=400)
#                             draft.edited_fields = current_package_edited
#                             draft.save()
#                             drafts_saved = True

#                         if proposed_package_edited:
#                             draft, created = ProposedPackageDetailsDraft.objects.get_or_create(employee_draft=employee_draft)
#                             for field, value in tabs.get('proposed_package', {}).items():
#                                 if field in ['increment_percentage', 'increased_fuel_amount', 'mobile_allowance_proposed', 'vehicle_proposed_id'] and proposed_package_edited.get('vehicle_id' if field == 'vehicle_proposed_id' else field):
#                                     try:
#                                         if field == 'vehicle_proposed_id':
#                                             draft.vehicle_id = int(value) if value else None
#                                         elif field == 'mobile_allowance_proposed':
#                                             draft.mobile_allowance = Decimal(value) if value else Decimal('0')
#                                         elif field in ['increment_percentage', 'increased_fuel_amount']:
#                                             draft.__setattr__(field, Decimal(value) if value else Decimal('0'))
#                                     except ValueError as e:
#                                         logger.error(f"Invalid value for {field} in proposed_package for employee {employee_id}: {str(e)}")
#                                         return JsonResponse({'error': f'Invalid value for {field}: {value}'}, status=400)
#                             draft.edited_fields = proposed_package_edited
#                             draft.save()
#                             drafts_saved = True

#                         if financial_impact_edited:
#                             draft, created = FinancialImpactPerMonthDraft.objects.get_or_create(employee_draft=employee_draft)
#                             for field, value in tabs.get('financial_impact', {}).items():
#                                 if field == 'emp_status_id' and financial_impact_edited.get(field):
#                                     try:
#                                         draft.emp_status_id = int(value) if value else None
#                                     except ValueError as e:
#                                         logger.error(f"Invalid emp_status_id {value} for employee {employee_id}: {str(e)}")
#                                         return JsonResponse({'error': f'Invalid emp_status_id: {value}'}, status=400)
#                             draft.edited_fields = financial_impact_edited
#                             draft.save()
#                             drafts_saved = True

#                 if drafts_saved:
#                     return JsonResponse({'message': 'Draft saved'})
#                 else:
#                     return JsonResponse({'message': 'No changes to save'}, status=200)
#         except Exception as e:
#             logger.error(f"Error in SaveDraftView for department {department_id}: {str(e)}", exc_info=True)
#             return JsonResponse({'error': str(e)}, status=500)

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
            drafts_saved = False
            with transaction.atomic():
                for employee_id, tabs in data.items():
                    employee = Employee.objects.filter(emp_id=employee_id, department_team_id=department_id).first()
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
                        if tab == 'employee':
                            for field, value in fields.items():
                                current_value = getattr(employee, field, None)
                                if field.endswith('_id'):
                                    current_value = getattr(getattr(employee, field.replace('_id', ''), None), 'id', None)
                                elif isinstance(current_value, bool):
                                    current_value = str(current_value).lower()
                                if str(value) != str(current_value):
                                    has_changes = True
                                    employee_draft_edited[field] = True

                        elif tab == 'current_package':
                            current_package = CurrentPackageDetails.objects.filter(employee=employee).first()
                            for field, value in fields.items():
                                current_value = getattr(current_package, field, None) if current_package else None
                                if field.endswith('_id'):
                                    current_value = current_value.id if current_value else None
                                if str(value) != str(current_value):
                                    has_changes = True
                                    current_package_edited[field] = True

                        elif tab == 'proposed_package':
                            proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first()
                            for field, value in fields.items():
                                current_value = getattr(proposed_package, field, None) if proposed_package else None
                                if field.endswith('_id'):
                                    current_value = current_value.id if current_value else None
                                if str(value) != str(current_value):
                                    has_changes = True
                                    proposed_package_edited[field] = True

                        elif tab == 'financial_impact':
                            financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first()
                            for field, value in fields.items():
                                current_value = getattr(financial_impact, field, None) if financial_impact else None
                                if field.endswith('_id'):
                                    current_value = current_value.id if current_value else None
                                if str(value) != str(current_value):
                                    has_changes = True
                                    financial_impact_edited[field] = True

                    if not has_changes:
                        continue

                    # Create or update EmployeeDraft
                    employee_draft = EmployeeDraft.objects.filter(employee=employee).first()
                    if not employee_draft:
                        employee_draft = EmployeeDraft(employee=employee, company=employee.company, department_team=employee.department_team)

                    # Save employee fields
                    for field, value in tabs.get('employee', {}).items():
                        if employee_draft_edited.get(field):
                            if field.endswith('_id'):
                                setattr(employee_draft, field, int(value) if value else None)
                            elif isinstance(getattr(EmployeeDraft, field).field, models.BooleanField):
                                setattr(employee_draft, field, value == 'true')
                            else:
                                setattr(employee_draft, field, value or None)

                    employee_draft.edited_fields = employee_draft_edited
                    if employee_draft_edited:
                        employee_draft.save()
                        drafts_saved = True

                    # Save current package fields
                    if current_package_edited:
                        draft, _ = CurrentPackageDetailsDraft.objects.get_or_create(employee_draft=employee_draft)
                        for field, value in tabs.get('current_package', {}).items():
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
                        draft, _ = ProposedPackageDetailsDraft.objects.get_or_create(employee_draft=employee_draft)
                        for field, value in tabs.get('proposed_package', {}).items():
                            if proposed_package_edited.get(field):
                                if field.endswith('_id'):
                                    setattr(draft, field, int(value) if value else None)
                                elif isinstance(getattr(ProposedPackageDetailsDraft, field).field, models.BooleanField):
                                    setattr(draft, field, value == 'true')
                                else:
                                    setattr(draft, field, Decimal(value) if value else Decimal('0'))
                        draft.edited_fields = proposed_package_edited
                        draft.save()
                        drafts_saved = True

                    # Save financial impact fields
                    if financial_impact_edited:
                        draft, _ = FinancialImpactPerMonthDraft.objects.get_or_create(employee_draft=employee_draft)
                        for field, value in tabs.get('financial_impact', {}).items():
                            if financial_impact_edited.get(field):
                                if field.endswith('_id'):
                                    setattr(draft, field, int(value) if value else None)
                                else:
                                    setattr(draft, field, Decimal(value) if value else Decimal('0'))
                        draft.edited_fields = financial_impact_edited
                        draft.save()
                        drafts_saved = True

                return JsonResponse({'message': 'Draft saved' if drafts_saved else 'No changes to save'}, status=200)

        except Exception as e:
            logger.error(f"Error in SaveDraftView for department {department_id}: {str(e)}", exc_info=True)
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
#                     employee = Employee.objects.filter(emp_id=employee_id, department_team_id=department_id).first()
#                     if not employee:
#                         return JsonResponse({'error': f'Employee {employee_id} not found'}, status=404)

#                     employee_draft = EmployeeDraft.objects.filter(employee=employee).first()
#                     if employee_draft and employee_draft.edited_fields:  # Only process if draft has edited fields
#                         for tab, fields in tabs.items():
#                             if tab == 'employee':
#                                 for field, value in fields.items():
#                                     if field in ['fullname', 'department_group_id', 'section_id', 'designation_id', 'location_id', 'date_of_joining', 'resign', 'date_of_resignation', 'remarks']:
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
#                                         elif field == 'date_of_joining' or field == 'date_of_resignation':
#                                             employee.__setattr__(field, value or None)
#                                         elif field == 'fullname' or field == 'remarks':
#                                             employee.__setattr__(field, value or None)
#                                 employee.save()

#                             elif tab == 'current_package':
#                                 current_package, created = CurrentPackageDetails.objects.get_or_create(employee=employee)
#                                 for field, value in fields.items():
#                                     if field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'mobile_allowance']:
#                                         if field == 'vehicle_id':
#                                             current_package.vehicle_id = int(value) if value else None
#                                         elif field in ['gross_salary', 'fuel_limit', 'mobile_allowance']:
#                                             current_package.__setattr__(field, Decimal(value) if value else Decimal('0'))
#                                 current_package.save()

#                             elif tab == 'proposed_package':
#                                 proposed_package, created = ProposedPackageDetails.objects.get_or_create(employee=employee)
#                                 for field, value in fields.items():
#                                     if field in ['increment_percentage', 'increased_fuel_amount', 'mobile_allowance_proposed', 'vehicle_proposed_id']:
#                                         if field == 'vehicle_proposed_id':
#                                             proposed_package.vehicle_id = int(value) if value else None
#                                         elif field == 'mobile_allowance_proposed':
#                                             proposed_package.mobile_allowance = Decimal(value) if value else Decimal('0')
#                                         elif field in ['increment_percentage', 'increased_fuel_amount']:
#                                             proposed_package.__setattr__(field, Decimal(value) if value else Decimal('0'))
#                                 proposed_package.save()

#                             elif tab == 'financial_impact':
#                                 financial_impact, created = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
#                                 for field, value in fields.items():
#                                     if field == 'emp_status_id':
#                                         financial_impact.emp_status_id = int(value) if value else None
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


'''
updated code for save final
'''

from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator


logger = logging.getLogger(__name__)

class SaveFinalView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    @method_decorator(require_POST)
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
                        logger.info(f"Updating employee {employee_id}: {emp_data}")
                        for field, value in emp_data.items():
                            if field in [
                                'fullname', 'department_group_id', 'section_id',
                                'designation_id', 'location_id', 'date_of_joining',
                                'resign', 'date_of_resignation', 'eligible_for_increment', 'remarks'
                            ]:
                                if field in ['department_group_id', 'section_id', 'designation_id', 'location_id']:
                                    setattr(employee, field, int(value) if value else None)
                                elif field in ['resign', 'eligible_for_increment']:
                                    setattr(employee, field, value == 'true')
                                elif field in ['date_of_joining', 'date_of_resignation', 'fullname', 'remarks']:
                                    setattr(employee, field, value or None)
                        employee.save()

                    # Current Package Tab
                    if "current_package" in tabs:
                        pkg_data = tabs["current_package"]
                        logger.info(f"Updating current_package {employee_id}: {pkg_data}")
                        current_pkg, _ = CurrentPackageDetails.objects.get_or_create(employee=employee)
                        for field, value in pkg_data.items():
                            if field in ['gross_salary', 'vehicle_id', 'fuel_limit', 'fuel_litre', 'mobile_provided']:
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
                        for field, value in prop_data.items():
                            if field in [
                                'increment_percentage', 'increased_fuel_amount', 'fuel_litre',
                                'vehicle_allowance', 'mobile_provided', 'approved'
                            ]:
                                if field == 'vehicle_id':  # Adjust if vehicle_id is used
                                    proposed_pkg.vehicle_id = int(value) if value else None
                                elif field in ['mobile_provided', 'approved']:
                                    setattr(proposed_pkg, field, value == 'true')
                                else:
                                    setattr(proposed_pkg, field, Decimal(value) if value else Decimal('0'))
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


