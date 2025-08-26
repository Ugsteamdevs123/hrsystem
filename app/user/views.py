from rest_framework.views import APIView
from rest_framework.response import Response


from .serializers import (
    UserLoginSerializer,
)
from .models import (
    CustomUser,
    Company,
    Section,
    VehicleInfo,
    VehicleModel
)

from django.contrib.auth import login, logout
from rest_framework import status
from django.middleware.csrf import get_token
from rest_framework.permissions import AllowAny , IsAuthenticated
from rest_framework.authentication import SessionAuthentication

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
    VehicleInfoForm,
    VehicleModelForm

)

# Create your views here.

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
    permission_required = "user.view_vehicleinfo"
    template_name = "view_vehicle_list.html"

    def get(self, request):
        vehicles = VehicleInfo.objects.select_related("vehicle", "ownership_type").all()
        return render(request, self.template_name, {"vehicles": vehicles})


# --- ADD VEHICLE ---
class AddVehicleView(PermissionRequiredMixin, View):
    permission_required = "user.add_vehicleinfo"
    template_name = "add_vehicle.html"

    def get(self, request):
        vehicle_form = VehicleModelForm()
        info_form = VehicleInfoForm()
        return render(request, self.template_name, {
            "vehicle_form": vehicle_form,
            "info_form": info_form
        })

    def post(self, request):
        vehicle_form = VehicleModelForm(request.POST)
        info_form = VehicleInfoForm(request.POST)
        if vehicle_form.is_valid() and info_form.is_valid():
            vehicle = vehicle_form.save()
            info = info_form.save(commit=False)
            info.vehicle = vehicle
            info.save()
            messages.success(request, "Vehicle added successfully!")
            return redirect("view_vehicles")
        return render(request, self.template_name, {
            "vehicle_form": vehicle_form,
            "info_form": info_form
        })


# --- UPDATE VEHICLE ---
class UpdateVehicleView(PermissionRequiredMixin, View):
    permission_required = "user.change_vehicleinfo"
    template_name = "update_vehicle.html"

    def get(self, request, pk):
        vehicle_info = get_object_or_404(VehicleInfo, pk=pk)
        vehicle_form = VehicleModelForm(instance=vehicle_info.vehicle)
        info_form = VehicleInfoForm(instance=vehicle_info)
        return render(request, self.template_name, {
            "vehicle_form": vehicle_form,
            "info_form": info_form,
            "vehicle_info": vehicle_info
        })

    def post(self, request, pk):
        vehicle_info = get_object_or_404(VehicleInfo, pk=pk)
        vehicle_form = VehicleModelForm(request.POST, instance=vehicle_info.vehicle)
        info_form = VehicleInfoForm(request.POST, instance=vehicle_info)
        if vehicle_form.is_valid() and info_form.is_valid():
            vehicle_form.save()
            info_form.save()
            messages.success(request, "Vehicle updated successfully!")
            return redirect("view_vehicles")
        return render(request, self.template_name, {
            "vehicle_form": vehicle_form,
            "info_form": info_form,
            "vehicle_info": vehicle_info
        })


# --- DELETE VEHICLE ---
class DeleteVehicleView(PermissionRequiredMixin, View):
    permission_required = "user.delete_vehicleinfo"

    def get(self, request, pk):
        vehicle_info = get_object_or_404(VehicleInfo, pk=pk)
        vehicle_info.delete()  # Hard delete, or you can soft delete by adding a flag
        messages.success(request, "Vehicle deleted successfully!")
        return redirect("view_vehicles")














from venv import logger
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.messages import success as messages_success
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import View
from django.contrib.sessions.models import Session

from permissions import GroupOrSuperuserPermission, PermissionRequiredMixin

from .models import (
    hr_assigned_companies,
    DepartmentTeams,
    IncrementDetailsSummary,
    Company,
    Employee,
    CurrentPackageDetails,
    ProposedPackageDetails,
    FinancialImpactPerMonth,
    DepartmentGroups,
    Designation,
    Location
)

from .utils import get_companies_and_department_teams
from .serializer import (
    IncrementDetailsSummarySerializer,
    DepartmentGroupsSerializer,
    DesignationSerializer,
    DesignationCreateSerializer,
    LocationsSerializer,
    VehicleInfoDropdownSerializer

)
from collections import defaultdict
import json
from django.core.exceptions import PermissionDenied
from django.db import transaction





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
        department = DepartmentTeams.objects.filter(
            id=department_id,
            company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
        ).first()
        if not department:
            return render(request, 'error.html', {'error': 'Invalid department'}, status=400)

        company_data = get_companies_and_department_teams(request.user)

        employees = Employee.objects.filter(department_team=department)
        joined_data = []
        for employee in employees:
            current_package = CurrentPackageDetails.objects.filter(employee=employee).first() or {}
            proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first() or {}
            financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first() or {}
            joined_data.append({
                'employee_id': employee.emp_id,
                'fullname': employee.fullname,
                'company': employee.company.name,
                'department_team': employee.department_team.name if employee.department_team else '',
                'department_group': employee.department_group.name if employee.department_group else '',
                'section': employee.section.name if employee.section else '',
                'designation': employee.designation.title if employee.designation else '',
                'location': employee.location.location if employee.location else '',
                'date_of_joining': employee.date_of_joining or '',
                'resign': employee.resign,
                'date_of_resignation': employee.date_of_resignation or '',
                'remarks': employee.remarks or '',
                'image': employee.image.url if employee.image else '',
                'gross_salary': current_package.gross_salary if current_package else '',
                
                # 'vehicle': current_package.vehicle if current_package else '',
                # 'vehicle': current_package.vehicle.vehicle_model.name if current_package and current_package.vehicle else '',
                'vehicle': current_package.vehicle.vehicle.brand.name if current_package and current_package.vehicle else '',

                'fuel_limit': current_package.fuel_limit if current_package else '',
                'mobile_allowance_current': current_package.mobile_allowance if current_package else '',
                'increment_percentage': proposed_package.increment_percentage if proposed_package else '',
                'increased_amount': proposed_package.increased_amount.formula if proposed_package and proposed_package.increased_amount else '',
                'revised_salary': proposed_package.revised_salary.formula if proposed_package and proposed_package.revised_salary else '',
                'increased_fuel_amount': proposed_package.increased_fuel_amount if proposed_package else '',
                'revised_fuel_allowance': proposed_package.revised_fuel_allowance.formula if proposed_package and proposed_package.revised_fuel_allowance else '',
                'mobile_allowance_proposed': proposed_package.mobile_allowance if proposed_package else '',
                
                # 'vehicle_proposed': proposed_package.vehicle if proposed_package else '',
                'vehicle_proposed': proposed_package.vehicle.vehicle.brand.name if proposed_package and proposed_package.vehicle else '',

                'emp_status': financial_impact.emp_status.name if financial_impact and financial_impact.emp_status else '',
                'serving_years': financial_impact.serving_years if financial_impact else '',
                'salary': financial_impact.salary if financial_impact else '',
                'gratuity': financial_impact.gratuity.formula if financial_impact and financial_impact.gratuity else '',
                'bonus': financial_impact.bonus.formula if financial_impact and financial_impact.bonus else '',
                'leave_encashment': financial_impact.leave_encashment.formula if financial_impact and financial_impact.leave_encashment else '',
                'mobile_allowance_financial': financial_impact.mobile_allowance.formula if financial_impact and financial_impact.mobile_allowance else '',
                'fuel': financial_impact.fuel if financial_impact else '',
                'total': financial_impact.total.formula if financial_impact and financial_impact.total else '',
            })

        if joined_data:
            table_html = '<div class="table-responsive"><table class="table table-striped table-hover">'
            table_html += '<thead><tr>'
            for key in joined_data[0].keys():
                table_html += f'<th>{key.replace("_", " ").title()}</th>'
            table_html += '<th>Actions</th></tr></thead><tbody>'
            for row in joined_data:
                table_html += f'<tr data-employee-id="{row["employee_id"]}">'
                for value in row.values():
                    table_html += f'<td>{value if value is not None else ""}</td>'
                table_html += '<td><button class="btn btn-sm btn-danger delete-employee-btn">Delete</button></td>'
                table_html += '</tr>'
            table_html += '</tbody></table></div>'
        else:
            table_html = '<p>No data available for this department.</p>'

        return render(request, 'department_table.html', {
            'department': department,
            'table_html': table_html,
            'department_id': department_id,
            'company_data': company_data
        })


# View for create employee data

class CreateDataView(View):
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
        return render(request, 'create_data.html', {
            'department_id': department_id,
            'company_id': department.company.id
        })

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

                        vehicle_id = request.POST.get('vehicle_id')  # vehicle_id instead of vehicle
                        
                        employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                        current_package = CurrentPackageDetails.objects.create(
                            employee=employee,
                            gross_salary=request.POST.get('gross_salary'),
                            
                            vehicle_id=vehicle_id  if vehicle_id else None,  # Link to Vehicle instance,
                            
                            fuel_limit=request.POST.get('fuel_limit'),
                            mobile_allowance=request.POST.get('mobile_allowance')
                        )
                        logger.debug(f"CurrentPackageDetails created for employee: {employee_id}")
                        return JsonResponse({'message': 'Current Package created'})
                    elif step == 'proposed_package':
                        employee_id = request.POST.get('employee_id')

                        vehicle_id=request.POST.get('vehicle_id')  # vehicle_id instead of vehicle
                        
                        employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                        proposed_package = ProposedPackageDetails.objects.create(
                            employee=employee,
                            increment_percentage=request.POST.get('increment_percentage'),
                            increased_amount_id=request.POST.get('increased_amount_id'),
                            revised_salary_id=request.POST.get('revised_salary_id'),
                            increased_fuel_amount=request.POST.get('increased_fuel_amount'),
                            revised_fuel_allowance_id=request.POST.get('revised_fuel_allowance_id'),
                            mobile_allowance=request.POST.get('mobile_allowance'),

                            vehicle_id=vehicle_id if vehicle_id else None,  # Link to Vehicle instance
                        )
                        logger.debug(f"ProposedPackageDetails created for employee: {employee_id}")
                        return JsonResponse({'message': 'Proposed Package created'})
                    elif step == 'financial_impact':
                        employee_id = request.POST.get('employee_id')
                        employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                        financial_impact = FinancialImpactPerMonth.objects.create(
                            employee=employee,
                            emp_status_id=request.POST.get('emp_status_id'),
                            serving_years=request.POST.get('serving_years'),
                            salary=request.POST.get('salary'),
                            gratuity_id=request.POST.get('gratuity_id'),
                            bonus_id=request.POST.get('bonus_id'),
                            leave_encashment_id=request.POST.get('leave_encashment_id'),
                            mobile_allowance_id=request.POST.get('mobile_allowance_id'),
                            fuel=request.POST.get('fuel'),
                            total_id=request.POST.get('total_id')
                        )
                        logger.debug(f"FinancialImpactPerMonth created for employee: {employee_id}")
                        return JsonResponse({'message': 'Financial Impact created'})
                return JsonResponse({'error': 'Invalid step'}, status=400)
            except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
                logger.error(f"Error in CreateDataView: {str(e)}")
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
            print(data)
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


class VehiclesDropdownView(View):
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            vehicles = VehicleInfo.objects.select_related('vehicle__brand').all()
            data = VehicleInfoDropdownSerializer(vehicles, many=True).data
            return JsonResponse({'data': data})
        return JsonResponse({'error': 'Invalid request'}, status=400)














